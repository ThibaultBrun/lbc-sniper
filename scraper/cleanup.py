"""Verifie une par une que les annonces actives existent toujours sur LBC.

Strategie : on ne verifie que les annonces "candidates" — celles dont
`last_seen_at` est plus vieux que la fenetre de scrape incremental (donc qu'on
n'a pas vues lors des derniers scrapes recents). Sur ces candidates, on appelle
`client.get_ad(id)` une par une avec un delai random pour ne pas reveiller
Datadome. Si l'API renvoie NotFoundError, on tag `is_active=false`.

Usage:
    python -m scraper.cleanup                  # toutes les categories
    python -m scraper.cleanup --watch <id>     # une seule
"""

import argparse
import random
import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

import lbc

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from .db import finish_run, get_client, start_run

# Seuil : on ne verifie que les annonces non vues depuis au moins X jours.
# En dessous, on fait confiance au scrape recent (incremental_hours=24 confirme
# tout ce qui est repasse dans le top des dernieres 24h). Au-dela, on doute
# vraiment qu'elles soient encore actives -> on verifie une par une.
# A 6 mois : c'est une duree de vie raisonnable pour une annonce VTT (au-dela
# le vendeur l'a probablement abandonnee), et ca limite drastiquement le nb
# de candidates a verifier (vs 3 jours qui en faisait beaucoup).
_CANDIDATE_AGE_HOURS = 24 * 30 * 6  # 6 mois

# Stop apres ce nombre d'erreurs consecutives (probable rate-limit / Datadome).
_CONSECUTIVE_ERROR_LIMIT = 5

# Delai aleatoire entre 2 requetes (en secondes).
_DELAY_MIN_S = 0.6
_DELAY_MAX_S = 0.9


def _fetch_candidates(db, watch_id: Optional[str]) -> list[dict]:
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=_CANDIDATE_AGE_HOURS)).isoformat()
    q = (
        db.table("ads")
        .select("id, subject, last_seen_at, watch_id")
        .eq("is_active", True)
        .lt("last_seen_at", cutoff)
        .order("last_seen_at", desc=False)  # les plus vieilles en premier
    )
    if watch_id:
        q = q.eq("watch_id", watch_id)
    return q.execute().data


def cleanup(watch_id: Optional[str] = None) -> int:
    db = get_client()
    candidates = _fetch_candidates(db, watch_id)
    print(f"Found {len(candidates)} candidates to verify (active + last_seen >{_CANDIDATE_AGE_HOURS}h ago)")

    if not candidates:
        return 0

    client = lbc.Client()
    run_id = start_run(db, watch_id or "*", "cleanup")

    deactivated = 0
    confirmed = 0
    consecutive_errors = 0
    rate_limited = False

    now_iso = datetime.now(timezone.utc).isoformat()

    for i, ad in enumerate(candidates, 1):
        ad_id = ad["id"]
        try:
            client.get_ad(ad_id=ad_id)
            # Annonce toujours en ligne -> on rafraichit last_seen_at
            db.table("ads").update({"last_seen_at": now_iso}).eq("id", ad_id).execute()
            confirmed += 1
            consecutive_errors = 0
            print(f"  [{i}/{len(candidates)}] [{ad_id}] OK alive | {ad['subject'][:50]}")
        except lbc.exceptions.NotFoundError:
            db.table("ads").update({"is_active": False}).eq("id", ad_id).execute()
            deactivated += 1
            consecutive_errors = 0
            print(f"  [{i}/{len(candidates)}] [{ad_id}] DEAD - deactivated | {ad['subject'][:50]}")
        except lbc.exceptions.DatadomeError as e:
            consecutive_errors += 1
            print(f"  [{i}/{len(candidates)}] [{ad_id}] datadome 403: {e}", file=sys.stderr)
            if consecutive_errors >= _CONSECUTIVE_ERROR_LIMIT:
                print(
                    f"\n!!! {consecutive_errors} echecs Datadome consecutifs - "
                    f"abandon. Reessaie plus tard.",
                    file=sys.stderr,
                )
                rate_limited = True
                break
        except Exception as e:
            consecutive_errors += 1
            print(f"  [{i}/{len(candidates)}] [{ad_id}] error: {type(e).__name__}: {e}", file=sys.stderr)
            if consecutive_errors >= _CONSECUTIVE_ERROR_LIMIT:
                print(f"\n!!! {consecutive_errors} erreurs consecutives, abandon.", file=sys.stderr)
                break

        # Delai humain aleatoire avant la requete suivante
        if i < len(candidates):
            delay = random.uniform(_DELAY_MIN_S, _DELAY_MAX_S)
            time.sleep(delay)

    finish_run(
        db, run_id,
        ads_processed=confirmed + deactivated,
        ads_new=deactivated,
        ads_updated=confirmed,
        error="datadome rate limit" if rate_limited else None,
    )

    print(f"\n=== Cleanup: {confirmed} alive, {deactivated} deactivated"
          + (f", aborted on rate limit" if rate_limited else "")
          + " ===")
    return 2 if rate_limited else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cleanup deactivated ads via LBC API")
    parser.add_argument("--watch", help="Limit to a single watch_id")
    args = parser.parse_args()
    sys.exit(cleanup(args.watch))
