"""Scan complet LBC sans fenetre temporelle ni enrichissement IA.

Usage:
    python -m scraper.scripts.full_scan
    python -m scraper.scripts.full_scan --watch vtt-bayonne

Le script reprend les watches de config.yaml, force une pagination LBC complete
en limit=100, applique les filtres locaux habituels, puis upsert en Supabase.
Il ne lance ni cleanup, ni enricher, ni notifier.
"""

import argparse
import sys
import time
from dataclasses import replace

import lbc

from ..config import load_config
from ..db import finish_run, get_client, start_run, upsert_ads
from ..fetcher import _ad_to_fetched, _apply_filters, _build_search_kwargs


def _fetch_all_pages(client: lbc.Client, watch) -> list:
    kwargs = _build_search_kwargs(watch)
    kwargs["limit"] = 100

    all_ads = []
    seen_ids = set()
    max_pages = None
    page = 1

    while True:
        result = client.search(page=page, **kwargs)
        if max_pages is None:
            max_pages = result.max_pages
            print(f"    LBC total={result.total_all}, max_pages={max_pages}")

        if not result.ads:
            break

        new_in_page = 0
        for raw_ad in result.ads:
            if raw_ad.id in seen_ids:
                continue
            seen_ids.add(raw_ad.id)
            all_ads.append(_ad_to_fetched(raw_ad))
            new_in_page += 1

        print(f"    page {page}: +{new_in_page} (raw total {len(all_ads)})")

        if max_pages and page >= max_pages:
            break

        page += 1

    return all_ads


def run(watch_id_filter: str | None = None, text: str | None = None) -> int:
    watches = load_config("config.yaml")
    if watch_id_filter:
        watches = [w for w in watches if w.id == watch_id_filter]
        if not watches:
            print(f"No watch with id '{watch_id_filter}'", file=sys.stderr)
            return 1

    db = get_client()
    client = lbc.Client()

    total_new = 0
    total_updated = 0
    failed: list[str] = []

    for watch in watches:
        if text is not None:
            watch = replace(watch, text=text, search_in_title_only=False)
        print(f"\n=== FULL SCAN {watch.label} ({watch.id}) ===")
        if watch.text:
            print(f"  text: {watch.text}")
        run_id = start_run(db, watch.id, "full_scan")
        try:
            t0 = time.time()
            raw_ads = _fetch_all_pages(client, watch)
            filtered = _apply_filters(raw_ads, watch)
            elapsed = time.time() - t0
            print(f"  raw fetched: {len(raw_ads)}")
            print(f"  after local filters: {len(filtered)}")
            print(f"  duration: {elapsed:.1f}s")

            new, updated = upsert_ads(
                db, watch.id, filtered, category_label=watch.category_label
            )
            print(f"  upsert: {new} new, {updated} updated")

            finish_run(
                db,
                run_id,
                ads_processed=len(filtered),
                ads_new=new,
                ads_updated=updated,
            )
            total_new += new
            total_updated += updated
        except Exception as e:
            msg = f"{type(e).__name__}: {e}"
            print(f"  FAILED: {msg}", file=sys.stderr)
            import traceback

            traceback.print_exc()
            finish_run(db, run_id, error=msg)
            failed.append(watch.id)

    print(f"\n=== Full scan summary: {total_new} new, {total_updated} updated, {len(failed)} failed ===")
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Full LBC scan without AI enrichment")
    parser.add_argument("--watch", help="Run only the watch with this id")
    parser.add_argument("--text", help="Override search text to shard/cible a full scan")
    args = parser.parse_args()
    return run(args.watch, text=args.text)


if __name__ == "__main__":
    sys.exit(main())
