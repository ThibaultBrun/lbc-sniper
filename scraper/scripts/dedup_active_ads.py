"""Desactive les doublons actifs en gardant l'annonce la plus recente.

Deux strategies sont appliquees :
1. Doublon strict : subject normalise + city + price (meme logique que db.py).
2. Doublon enrichi : brand + model + year + price + city, seulement si brand ou
   model est renseigne (pour eviter les faux positifs sur des annonces non
   enrichies qui ont juste le meme prix dans la meme ville).

Usage:
    python -m scraper.scripts.dedup_active_ads --dry-run
    python -m scraper.scripts.dedup_active_ads
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from ..db import _fingerprint, get_client


FIELDS = (
    "id,subject,city,current_price,brand,model,year,first_seen_at,last_seen_at,"
    "is_active,url"
)


def _norm(value: Any) -> str:
    return str(value).strip().lower() if value is not None else ""


def _semantic_key(row: dict) -> str | None:
    if not (row.get("brand") or row.get("model")):
        return None
    price = row.get("current_price")
    price_part = str(int(float(price))) if price is not None else ""
    return "|".join(
        [
            _norm(row.get("brand")),
            _norm(row.get("model")),
            str(row.get("year") or ""),
            price_part,
            _norm(row.get("city")),
        ]
    )


def _sort_key(row: dict) -> tuple[str, int]:
    return (str(row.get("first_seen_at") or ""), int(row.get("id") or 0))


def _fetch_active_ads(db) -> list[dict]:
    rows: list[dict] = []
    page = 0
    page_size = 1000
    while True:
        batch = (
            db.table("ads")
            .select(FIELDS)
            .eq("is_active", True)
            .order("id")
            .range(page * page_size, (page + 1) * page_size - 1)
            .execute()
            .data
            or []
        )
        rows.extend(batch)
        if len(batch) < page_size:
            return rows
        page += 1


def _group_duplicates(rows: list[dict], mode: str) -> dict[str, list[dict]]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if mode == "strict":
            key = _fingerprint(row.get("subject"), row.get("city"), row.get("current_price"))
        else:
            key = _semantic_key(row)
        if key:
            groups[key].append(row)
    return {k: v for k, v in groups.items() if len(v) > 1}


def _pick_deactivations(groups: dict[str, list[dict]]) -> dict[int, dict]:
    to_deactivate: dict[int, dict] = {}
    for key, rows in groups.items():
        keep = max(rows, key=_sort_key)
        for row in rows:
            if row["id"] == keep["id"]:
                continue
            to_deactivate[row["id"]] = {
                "row": row,
                "kept": keep,
                "key": key,
            }
    return to_deactivate


def run(dry_run: bool = False) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    db = get_client()
    rows = _fetch_active_ads(db)
    strict = _group_duplicates(rows, "strict")
    semantic = _group_duplicates(rows, "semantic")

    deactivations = _pick_deactivations(strict)
    deactivations.update(_pick_deactivations(semantic))

    print(f"active rows: {len(rows)}")
    print(f"strict duplicate groups: {len(strict)}")
    print(f"semantic duplicate groups: {len(semantic)}")
    print(f"ads to deactivate: {len(deactivations)}")

    for ad_id, item in sorted(deactivations.items()):
        row = item["row"]
        kept = item["kept"]
        print(
            f"  deactivate {ad_id} -> keep {kept['id']} | "
            f"{row.get('current_price')} EUR | {row.get('city')} | {row.get('subject')}"
        )

    if dry_run or not deactivations:
        return 0

    now = datetime.now(timezone.utc).isoformat()
    ids = sorted(deactivations)
    db.table("ads").update({"is_active": False, "last_seen_at": now}).in_("id", ids).execute()
    print(f"done: deactivated {len(ids)} duplicate ad(s)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Deactivate active duplicate ads")
    parser.add_argument("--dry-run", action="store_true", help="Print only, do not update DB")
    args = parser.parse_args()
    return run(dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
