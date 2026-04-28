"""Point d'entrée du scraper. Pour chaque watch:
1. Fetch les annonces sur LBC via la lib `lbc`
2. Upsert dans Supabase (avec historique de prix si changement)
3. Log un run dans la table `runs`

Usage:
    python -m scraper.main                     # Scrape tous les watches
    python -m scraper.main --watch vtt-enduro-bayonne
"""

import argparse
import sys
import traceback

# Windows console cp1252 → on force UTF-8 pour ne pas crash sur les emojis
# qu'on retrouve parfois dans les titres LBC.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import lbc

from .config import load_config
from .db import deactivate_stale_ads, finish_run, get_client, start_run, upsert_ads
from .fetcher import fetch_watch


def run(watch_id_filter: str | None = None) -> int:
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
        print(f"\n=== {watch.label} ({watch.id}) ===")
        run_id = start_run(db, watch.id, "scrape")
        try:
            ads = fetch_watch(client, watch)
            print(f"  fetched {len(ads)} ads from LBC")
            new, updated = upsert_ads(db, watch.id, ads)
            print(f"  upsert: {new} new, {updated} updated")

            # Cleanup : désactive les annonces disparues de LBC. Si LBC nous a
            # renvoyé moins que la limite, c'est exhaustif → on désactive direct.
            # Sinon on tolère 3 jours d'absence avant désactivation.
            seen_ids = [a.id for a in ads]
            fetch_was_complete = len(ads) < watch.limit
            stale = deactivate_stale_ads(
                db, watch.id, seen_ids, fetch_was_complete=fetch_was_complete
            )
            if stale:
                tag = "exhaustive" if fetch_was_complete else "after grace period"
                print(f"  deactivated {stale} stale ads ({tag})")

            finish_run(db, run_id, ads_processed=len(ads), ads_new=new, ads_updated=updated)
            total_new += new
            total_updated += updated
        except lbc.exceptions.DatadomeError as e:
            msg = f"Datadome blocked: {e}"
            print(f"  FAILED: {msg}", file=sys.stderr)
            finish_run(db, run_id, error=msg)
            failed.append(watch.id)
        except Exception as e:
            msg = f"{type(e).__name__}: {e}"
            print(f"  FAILED: {msg}", file=sys.stderr)
            traceback.print_exc()
            finish_run(db, run_id, error=msg)
            failed.append(watch.id)

    print(f"\n=== Summary: {total_new} new, {total_updated} updated, {len(failed)} failed ===")
    return 1 if failed else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LBC scraper")
    parser.add_argument("--watch", help="Run only the watch with this id")
    args = parser.parse_args()
    sys.exit(run(args.watch))
