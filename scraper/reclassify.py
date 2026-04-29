"""Reclassif rapide des annonces existantes : applique le mapping marque/modele
de scraper/vtt_categories.py sur toutes les annonces deja enrichies (qui ont
brand+model renseignes), sans appeler Claude.

Pour les annonces ou le mapping ne match pas, on reste a vtt_category=NULL —
elles seront classifiees au prochain enrichissement (passe IA), ou bien on
peut relancer un enricher avec --reset-enrichment-burst sur des modeles
specifiques.

Usage : python -m scraper.reclassify
        python -m scraper.reclassify --dry-run     # log seulement
"""

import argparse
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from .db import get_client
from .vtt_categories import classify_by_model


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true", help="Affiche sans ecrire en base")
    p.add_argument("--limit", type=int, default=10000, help="Max ads a traiter")
    args = p.parse_args()

    db = get_client()

    # On prend tout ce qui est enrichi (brand+model present), categorisable ou non.
    # Inutile de filtrer sur vtt_category IS NULL : on veut aussi mettre a jour
    # si la classification a evolue depuis (ex : nouveau mapping ajoute).
    rows = (
        db.table("ads")
        .select("id, brand, model, vtt_category, category_label")
        .not_.is_("brand", "null")
        .not_.is_("model", "null")
        .limit(args.limit)
        .execute()
        .data
    )
    print(f"=== Reclassify : {len(rows)} ads avec brand+model ===")

    counts: dict[str, int] = {}
    matched = 0
    unchanged = 0
    written = 0
    unmapped = 0

    for r in rows:
        cat = classify_by_model(r.get("brand"), r.get("model"))
        if cat is None:
            unmapped += 1
            continue
        matched += 1
        counts[cat] = counts.get(cat, 0) + 1
        if r.get("vtt_category") == cat:
            unchanged += 1
            continue
        if args.dry_run:
            print(f"  [DRY] ad={r['id']} {r['brand']} {r['model']} -> {cat} (etait: {r.get('vtt_category')})")
            continue
        db.table("ads").update({"vtt_category": cat}).eq("id", r["id"]).execute()
        written += 1

    print()
    print(f"  matches mapping  : {matched}")
    print(f"  unchanged        : {unchanged}")
    print(f"  written          : {written}")
    print(f"  unmapped (NULL)  : {unmapped}")
    print(f"  par categorie    : {counts}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
