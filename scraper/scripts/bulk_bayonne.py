"""Scrape one-shot exhaustif: tous les VTT enduro + DH actifs dans un rayon
de 200km autour de Bayonne. Pagine completement (jusqu'a max_pages renvoye
par LBC), peu importe les dates de publication.

Usage: python -m scraper.scripts.bulk_bayonne

Ne touche pas au config.yaml. Les annonces sont taguees avec un watch_id
"bulk-bayonne-200-<text>" et le category_label habituel pour qu'elles
s'integrent au site comme des VTT enduro / VTT DH classiques.
"""
import sys
import time
from typing import Optional

import lbc

from ..db import deactivate_stale_ads, finish_run, get_client, start_run, upsert_ads
from ..fetcher import _ad_to_fetched, _apply_filters
from ..config import Watch, WatchLocation


CONFIGS = [
    {
        "id": "bulk-bayonne-200-enduro",
        "label": "BULK VTT Enduro - 200km Bayonne",
        "category_label": "VTT enduro",
        "text": "enduro",
        "enrichment_domain": "vtt_enduro",
    },
    {
        "id": "bulk-bayonne-200-dh",
        "label": "BULK VTT DH - 200km Bayonne",
        "category_label": "VTT DH",
        "text": "dh",
        "enrichment_domain": "vtt_dh",
    },
]


def fetch_all_pages(client: lbc.Client, text: str) -> list:
    """Pagine jusqu'a epuisement (max_pages indique par LBC)."""
    city = lbc.City(lat=43.4933, lng=-1.4747, radius=200_000, city="Bayonne")
    all_raw = []
    seen_ids = set()
    max_pages: Optional[int] = None

    page = 1
    while True:
        r = client.search(
            text=text,
            category=lbc.Category.VEHICULES_VELOS,
            locations=[city],
            limit=100,
            page=page,
            sort=lbc.Sort.NEWEST,
            search_in_title_only=True,
        )
        if max_pages is None:
            max_pages = r.max_pages
            print(f"    LBC says total={r.total_all}, max_pages={max_pages}")
        if not r.ads:
            break
        new_in_page = 0
        for ad in r.ads:
            if ad.id in seen_ids:
                continue
            seen_ids.add(ad.id)
            all_raw.append(ad)
            new_in_page += 1
        print(f"    page {page}: +{new_in_page} (total {len(all_raw)})")
        if max_pages and page >= max_pages:
            break
        page += 1
        if page > 50:  # garde-fou anti-boucle infinie
            break

    return all_raw


def main() -> int:
    db = get_client()
    client = lbc.Client()

    grand_total_new = 0
    grand_total_updated = 0

    for cfg in CONFIGS:
        print(f"\n=== {cfg['label']} ({cfg['id']}) ===")
        run_id = start_run(db, cfg["id"], "scrape")
        try:
            t0 = time.time()
            raw_ads = fetch_all_pages(client, cfg["text"])
            t1 = time.time()
            print(f"  fetched {len(raw_ads)} ads from LBC in {t1 - t0:.1f}s")

            # Filtre cote client : que les vrais velos (cat_id=55)
            fetched = [_ad_to_fetched(ad) for ad in raw_ads]
            # On reutilise _apply_filters via un Watch in-memory
            watch = Watch(
                id=cfg["id"], label=cfg["label"], category="VEHICULES_VELOS",
                text=cfg["text"], location=WatchLocation(city="Bayonne", lat=43.4933, lng=-1.4747, radius_km=200),
                price_max=None, limit=100, accept_category_ids=["55"],
                enrichment_domain=cfg["enrichment_domain"], category_label=cfg["category_label"],
            )
            filtered = _apply_filters(fetched, watch)
            print(f"  after cat=55 filter: {len(filtered)} real VTT")

            new, updated = upsert_ads(db, watch.id, filtered, category_label=watch.category_label)
            print(f"  upsert: {new} new, {updated} updated")

            seen_ids = [a.id for a in filtered]
            stale = deactivate_stale_ads(db, watch.id, seen_ids, fetch_was_complete=True)
            if stale:
                print(f"  deactivated {stale} stale ads")

            finish_run(db, run_id, ads_processed=len(filtered), ads_new=new, ads_updated=updated)
            grand_total_new += new
            grand_total_updated += updated
        except Exception as e:
            print(f"  FAILED: {type(e).__name__}: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            finish_run(db, run_id, error=str(e))

    print(f"\n=== Bulk summary: {grand_total_new} new, {grand_total_updated} updated ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
