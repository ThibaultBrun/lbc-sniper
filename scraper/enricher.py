"""Enrichit les annonces non encore traitées en appelant le CLI Claude.

Pour chaque annonce :
1. Construit un prompt expert + JSON schema attendu
2. Lance `claude -p --output-format json --json-schema <schema> --model <m> <prompt>`
3. Parse la réponse, extrait `structured_output`
4. Update la ligne `ads` dans Supabase

Usage:
    python -m scraper.enricher                          # tous les watches
    python -m scraper.enricher --watch vtt-enduro-bayonne
    python -m scraper.enricher --model haiku --limit 5  # mode test rapide
"""

import argparse
import json
import shutil
import subprocess
import sys
from typing import Optional

from .db import (
    fetch_unenriched_ads,
    finish_run,
    get_client,
    start_run,
    update_enrichment,
    update_enrichment_error,
)

CLAUDE_TIMEOUT_S = 90

# Schema JSON pour --json-schema. Les champs facultatifs sont nullable côté
# Pydantic / Claude (= "null" autorisé).
SCHEMA = {
    "type": "object",
    "properties": {
        "brand": {"type": ["string", "null"]},
        "model": {"type": ["string", "null"]},
        "year": {"type": ["integer", "null"]},
        "frame_material": {"type": ["string", "null"]},
        "wheel_size": {"type": ["string", "null"]},
        "electric": {"type": ["boolean", "null"]},
        "size_label": {"type": ["string", "null"]},
        "condition_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "estimated_market_eur": {"type": "number"},
        "deal_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "reasoning": {"type": "string"},
    },
    "required": [
        "brand", "model", "year", "electric",
        "condition_score", "estimated_market_eur", "deal_score", "reasoning",
    ],
}


DOMAIN_INTROS = {
    "vtt": "Tu es un expert du marche VTT d'occasion en France.",
    "vtt_enduro": (
        "Tu es un expert du marche VTT enduro/all-mountain d'occasion en France. "
        "Tu connais les modeles courants (Lapierre Zesty/Spicy, Specialized Enduro/Stumpjumper, "
        "Trek Slash/Remedy, Canyon Torque/Spectral/Strive, Commencal Meta/Clash, Santa Cruz Megatower/Bronson/Nomad, "
        "Cube Stereo, Orbea Occam/Rallon, BH Linx, Mondraker Crafty/Foxy, Haibike Alltrail) et leurs cotes."
    ),
    "voiture": "Tu es un expert du marche automobile d'occasion en France.",
    "moto": "Tu es un expert du marche moto d'occasion en France.",
}


def build_prompt(ad: dict, domain: Optional[str]) -> str:
    intro = DOMAIN_INTROS.get(domain or "", "Tu es un expert du marche francais d'occasion.")
    body = (ad.get("body") or "").strip()
    if len(body) > 1500:
        body = body[:1500] + "..."

    price = ad.get("current_price")
    price_str = f"{int(price)} EUR" if price else "Non indique"

    return f"""{intro}

Analyse cette annonce LeBonCoin et estime si c'est une bonne affaire.

Titre: {ad.get("subject", "")}
Prix demande: {price_str}
Ville: {ad.get("city") or "?"}
Description:
{body or "(vide)"}

Estime le prix de marche actuel pour ce vehicule/objet (en euros, valeur centrale).

Note de bon plan (deal_score):
- 0   = arnaque ou prix tres au-dessus du marche
- 30  = un peu cher
- 50  = au prix du marche
- 70  = clairement sous le marche
- 90+ = excellente affaire (>30% sous la cote, etat correct)

Note d'etat (condition_score):
- 0   = HS / pour pieces
- 50  = etat moyen, usure visible
- 80  = bon etat
- 95+ = quasi neuf

Reasoning: 2-3 phrases max. Mentionne pourquoi tu donnes ce score, et les points de vigilance (manque de photos, kilometrage suspect, modele recent vs ancien, etc.)."""


def call_claude(prompt: str, model: str = "opus") -> dict:
    """Appelle le CLI claude et retourne le `structured_output` parse.

    Lève RuntimeError si claude n'est pas trouve, timeout, ou JSON invalide.
    """
    if shutil.which("claude") is None:
        raise RuntimeError("CLI 'claude' introuvable dans PATH")

    cmd = [
        "claude",
        "-p",
        "--model", model,
        "--output-format", "json",
        "--json-schema", json.dumps(SCHEMA),
        prompt,
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=CLAUDE_TIMEOUT_S,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"claude CLI timeout after {CLAUDE_TIMEOUT_S}s") from e

    if proc.returncode != 0:
        raise RuntimeError(
            f"claude CLI exited {proc.returncode}: {proc.stderr.strip()[:300]}"
        )

    try:
        envelope = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"claude returned invalid JSON envelope: {e}") from e

    if envelope.get("is_error"):
        raise RuntimeError(f"claude reported error: {envelope.get('result', '')[:300]}")

    structured = envelope.get("structured_output")
    if not isinstance(structured, dict):
        raise RuntimeError(
            "no 'structured_output' in claude response — schema validation may have failed"
        )

    return structured


def enrich(
    watch_id: Optional[str] = None,
    limit: int = 50,
    model: str = "opus",
) -> int:
    db = get_client()
    pending = fetch_unenriched_ads(db, watch_id=watch_id, limit=limit)
    print(f"Found {len(pending)} unenriched ads (model={model})")

    if not pending:
        return 0

    # On regroupe par watch pour récupérer le domaine de chaque watch
    from .config import load_config
    watches = {w.id: w for w in load_config("config.yaml")}

    run_id = start_run(db, watch_id or "*", "enrich")
    ok = 0
    failed = 0

    for i, ad in enumerate(pending, 1):
        watch = watches.get(ad["watch_id"])
        domain = watch.enrichment_domain if watch else None

        print(f"\n[{i}/{len(pending)}] [{ad['id']}] {ad['subject'][:60]}")
        prompt = build_prompt(ad, domain)
        try:
            result = call_claude(prompt, model=model)
            update_enrichment(db, ad["id"], result, model=model)
            ok += 1
            print(
                f"  -> deal_score={result.get('deal_score')} "
                f"market={result.get('estimated_market_eur')}€ "
                f"brand={result.get('brand')} model={result.get('model')}"
            )
        except Exception as e:
            print(f"  FAILED: {e}", file=sys.stderr)
            try:
                update_enrichment_error(db, ad["id"], str(e), model=model)
            except Exception:
                pass
            failed += 1

    finish_run(
        db, run_id,
        ads_processed=ok + failed,
        ads_new=ok,
        error=f"{failed} failures" if failed else None,
    )

    print(f"\n=== Enrich summary: {ok} ok, {failed} failed ===")
    return 1 if failed and not ok else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enrich ads via claude CLI")
    parser.add_argument("--watch", help="Limit to a single watch_id")
    parser.add_argument("--limit", type=int, default=50, help="Max ads per run")
    parser.add_argument("--model", default="opus", help="claude model: opus or haiku")
    args = parser.parse_args()
    sys.exit(enrich(args.watch, args.limit, args.model))
