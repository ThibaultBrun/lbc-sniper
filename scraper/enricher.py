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

# Windows console est en cp1252 par defaut → crash sur les emojis dans les
# titres d'annonces. On force UTF-8 et on remplace les chars non encodables.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from .db import (
    fetch_active_ads,
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
        "pros": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 0,
            "maxItems": 6,
        },
        "cons": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 0,
            "maxItems": 6,
        },
    },
    "required": [
        "brand", "model", "year", "electric",
        "condition_score", "estimated_market_eur", "deal_score",
        "reasoning", "pros", "cons",
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
    "ludospace": (
        "Tu es un expert du marche automobile d'occasion en France et tu cherches "
        "specifiquement des LUDOSPACES (monospaces compacts familiaux derives d'utilitaires). "
        "Modeles cibles: Citroen Berlingo, Peugeot Partner/Rifter, Renault Kangoo, Fiat Doblo, "
        "VW Caddy, Opel Combo/Combo Life, Toyota Proace City Verso, Opel Vivaro Life, Nissan NV200, "
        "Citroen Spacetourer, Peugeot Traveller, VW Caravelle, Mercedes Citan/Vito Tourer. "
        "REGLE CRITIQUE: si l'annonce n'est PAS un ludospace (berline classique, SUV, sportive, "
        "fourgon tole utilitaire pur, pickup, etc.), donne un deal_score TRES bas (0-15) et explique-le "
        "clairement dans reasoning + cons (ex: 'pas un ludospace, c'est une Citroen C3'). "
        "Pour un vrai ludospace, evalue normalement: cote occasion realiste, kilometrage, motorisation, "
        "annee, options (climatisation, GPS, attelage), proprete de l'annonce."
    ),
    "ludospace_utilitaire": (
        "Tu es un expert du marche automobile d'occasion en France et tu cherches specifiquement "
        "des LUDOSPACES en version utilitaire AVEC AU MOINS 4 PLACES (cabine approfondie, banquette "
        "arriere amovible, type 'Crew Cab' / 'L1 5 places' / 'Multispace' / 'Combi'). "
        "Modeles cibles: Citroen Berlingo Multispace, Peugeot Partner Tepee/Rifter, Renault Kangoo, "
        "Fiat Doblo Cargo Combi, VW Caddy Maxi Life, Mercedes Vito Tourer/Mixto, Renault Trafic "
        "Combi/Passenger, Peugeot Expert Combi, Citroen Jumpy Combi, Opel Vivaro Combi, Ford Transit "
        "Custom Kombi, Toyota Proace Verso. "
        "REGLES CRITIQUES: "
        "(1) Si le vehicule a MOINS de 4 places (fourgon tole 2 ou 3 places sans banquette arriere), "
        "donne deal_score=0 et explique dans reasoning+cons que c'est exclu. "
        "(2) Si tu n'es PAS sur du nombre de places (annonce vague), donne un deal_score MAXIMUM de 30 "
        "et mentionne dans cons 'Nombre de places non confirme, risque utilitaire 2 places'. "
        "(3) Si c'est confirme 4+ places (banquette arriere, vitres laterales, ceintures arriere), "
        "evalue normalement le bon plan. "
        "Indices d'un vrai 4+ places: 'Combi', 'Multispace', 'Tepee', 'Combi Passenger', 'Mixto', "
        "mention de 5/7/9 places, photos avec banquette arriere visible."
    ),
    "voiture": (
        "Tu es un expert du marche automobile d'occasion en France, specialise dans "
        "les voitures familiales et utilitaires (ludospaces, monospaces compacts/grands, "
        "7 places). Tu connais les cotes des modeles courants : Citroen Berlingo, "
        "Peugeot Partner Tepee/Rifter, Renault Kangoo, Fiat Doblo, VW Caddy, Opel "
        "Combo/Combo Life, Dacia Dokker, Dacia Jogger, Ford Tourneo Connect/Courier, "
        "Toyota Proace City Verso, VW Touran/Sharan, Renault Scenic/Grand Scenic/Espace, "
        "Citroen C4 SpaceTourer, Grand C4 Picasso, Ford S-Max/Galaxy, Seat Alhambra, "
        "Kia Carens. Pour evaluer le bon plan : verifie l'annee, le kilometrage, "
        "la motorisation (essence/diesel/hybride/electrique), la boite (manuelle/auto), "
        "le nombre de portes/places, l'historique entretien, le controle technique. "
        "Le diesel ancien decote rapidement (ZFE, malus), l'essence/hybride se valorise "
        "mieux. Donne un deal_score qui reflete UNIQUEMENT l'ecart prix vs cote marche."
    ),
    "moto": (
        "Tu es un expert du marche moto d'occasion en France, specialise dans les "
        "cylindrees moyennes (125-500cc) accessibles en permis A2 ou A. "
        "Tu connais les segments: roadster (MT-07, CB500F, SV650, Z650, Duke 390), "
        "trail/aventure (V-Strom 250/650, NC750X, Tracer 700, F750GS), sportive "
        "(R3, Ninja 400/650, RS660), custom (Vulcan S, Rebel 500, Bolt), supermotard "
        "(Husqvarna 701, KTM 690 SMC), enduro/cross route-legaux (CRF300L, KTM EXC). "
        "Verifie age + kilometrage + entretien (chaine, pneus, plaquettes) et "
        "compatibilite permis dans tes pros/cons."
    ),
}


def build_prompt(ad: dict, domain: Optional[str]) -> str:
    intro = DOMAIN_INTROS.get(domain or "", "Tu es un expert du marche francais d'occasion.")
    body = (ad.get("body") or "").strip()
    if len(body) > 1500:
        body = body[:1500] + "..."

    price = ad.get("current_price")
    price_str = f"{int(price)} EUR" if price else "Non indique"

    # Attributs structures LBC : kilometrage, energie, boite, annee MEC, marque,
    # modele, cylindree, etat, etc. Ces champs sont fiables (saisis via formulaire
    # LBC), beaucoup plus que les infos en texte libre dans le body.
    attributes = ad.get("attributes") or {}
    # On filtre les attributs verbeux/inutiles (urls d'images, ids internes, etc.)
    skip_keys = {
        "profile_picture_url", "rating_score", "rating_count", "is_bundleable",
        "purchase_cta_visible", "negotiation_cta_visible", "country_isocode3166",
        "shipping_type", "shippable", "is_import", "vehicle_available_payment_methods",
        "vehicle_is_eligible_p2p", "estimated_parcel_size", "estimated_parcel_weight",
        "payment_methods", "stock_quantity", "activity_sector", "argus_object_id",
        "spare_parts_availability", "bicycode", "u_moto_brand", "u_moto_model",
        "u_moto_finition", "u_moto_version",
    }
    attr_lines = "\n".join(
        f"  - {k}: {v}" for k, v in sorted(attributes.items())
        if k not in skip_keys and v
    )
    attr_block = (
        f"\nAttributs structures LBC (fiables, saisis via formulaire) :\n{attr_lines}\n"
        if attr_lines
        else ""
    )

    return f"""{intro}

Analyse cette annonce LeBonCoin et estime si c'est une bonne affaire.

Titre: {ad.get("subject", "")}
Prix demande: {price_str}
Ville: {ad.get("city") or "?"}
{attr_block}
Description (texte libre du vendeur) :
{body or "(vide)"}

Estime le prix de marche actuel pour ce vehicule/objet (en euros, valeur centrale).

Note de bon plan (deal_score) — UNIQUEMENT basee sur l'ecart prix demande vs prix de marche estime :
- 0   = beaucoup plus cher que le marche
- 30  = un peu cher
- 50  = au prix du marche
- 70  = clairement sous le marche (-15 a -30%)
- 90+ = tres au-dessous du marche (>30% en dessous)

REGLE IMPORTANTE: ne baisse JAMAIS le deal_score parce que tu suspectes une arnaque,
un vol, ou que l'annonce paraitrait "trop belle pour etre vraie". On ne fait pas de
detection d'arnaque ici. Si le prix demande est tres bas vs marche, le deal_score
DOIT etre tres haut, point. Les doutes/verifications a faire vont dans `cons`, pas
dans le score.

Note d'etat (condition_score):
- 0   = HS / pour pieces
- 50  = etat moyen, usure visible
- 80  = bon etat
- 95+ = quasi neuf

Champs a remplir:
- reasoning: analyse detaillee (3-6 phrases) qui explique le score, situe le modele
  sur le marche (cote neuf / cote occasion typique), commente l'etat declare et
  rappelle l'enjeu (interet de cette annonce specifique).
- pros: 2-5 points forts concrets et factuels (ex: "carbone haut de gamme", "marque
  reputee Specialized", "annee recente 2023", "prix 40% sous la cote", "composants
  premium SRAM XX1", "vendeur professionnel").
- cons: 2-5 points de vigilance (ex: "absence de photos detaillees des suspensions",
  "modele ancien, pieces peut-etre obsoletes", "kilometrage non mentionne", "vendeur
  particulier, paiement en main propre uniquement", "annonce vague, manque de specs",
  "prix tres bas, verifier qu'il ne s'agit pas d'une arnaque").

Sois precis et factuel, evite les banalites. Si une info manque dans l'annonce, mentionne-le."""


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


# Si on a ce nombre d'echecs d'affilee, c'est probablement le quota Anthropic
# epuise (signal: claude CLI exited 1 sans stderr). On arrete le run pour ne
# pas marquer en erreur 100 annonces alors qu'il suffit d'attendre la prochaine
# fenetre de 5h.
_CONSECUTIVE_FAILURE_LIMIT = 5


def _reset_failed_burst(db, pending: list, current_index: int, burst_size: int) -> None:
    """Reset les enriched_at + enrich_error des `burst_size` dernieres annonces
    pour qu'elles soient re-essayees au prochain run."""
    start = max(0, current_index - burst_size)
    burst_ids = [pending[k]["id"] for k in range(start, current_index)]
    if not burst_ids:
        return
    try:
        db.table("ads").update(
            {"enriched_at": None, "enrich_error": None}
        ).in_("id", burst_ids).execute()
        print(f"  (reset {len(burst_ids)} ads to pending so the next run picks them up)")
    except Exception as e:
        print(f"  (failed to reset burst: {e})", file=sys.stderr)


def _process_one(db, ad: dict, watches: dict, model: str) -> bool:
    """Enrichit une annonce. Retourne True si succes, False si echec."""
    watch = watches.get(ad["watch_id"])
    domain = watch.enrichment_domain if watch else None
    prompt = build_prompt(ad, domain)
    try:
        result = call_claude(prompt, model=model)
        update_enrichment(db, ad["id"], result, model=model)
        print(
            f"  -> deal_score={result.get('deal_score')} "
            f"market={result.get('estimated_market_eur')}€ "
            f"brand={result.get('brand')} model={result.get('model')}"
        )
        return True
    except Exception as e:
        err_str = str(e)
        print(f"  FAILED: {err_str}", file=sys.stderr)
        try:
            update_enrichment_error(db, ad["id"], err_str, model=model)
        except Exception:
            pass
        return False


def _run_loop(db, pending: list, watches: dict, model: str) -> tuple[int, int, bool]:
    """Boucle principale d'enrichissement. Retourne (ok, failed, rate_limit_hit)."""
    ok = 0
    failed = 0
    consecutive = 0

    for i, ad in enumerate(pending, 1):
        print(f"\n[{i}/{len(pending)}] [{ad['id']}] {ad['subject'][:60]}")
        if _process_one(db, ad, watches, model):
            ok += 1
            consecutive = 0
            continue
        failed += 1
        consecutive += 1
        if consecutive >= _CONSECUTIVE_FAILURE_LIMIT:
            print(
                f"\n!!! {consecutive} echecs consecutifs - probable rate-limit "
                f"Claude (quota Opus epuise sur la fenetre 5h). Arret du run, "
                f"reessaie dans quelques heures.",
                file=sys.stderr,
            )
            _reset_failed_burst(db, pending, i, consecutive)
            return ok, failed, True

    return ok, failed, False


def enrich(
    watch_id: Optional[str] = None,
    limit: int = 50,
    model: str = "opus",
    reset: bool = False,
) -> int:
    db = get_client()
    if reset:
        pending = fetch_active_ads(db, watch_id=watch_id, limit=limit)
        print(f"[--reset] Re-enriching {len(pending)} active ads (model={model})")
    else:
        pending = fetch_unenriched_ads(db, watch_id=watch_id, limit=limit)
        print(f"Found {len(pending)} unenriched ads (model={model})")

    if not pending:
        return 0

    from .config import load_config
    watches = {w.id: w for w in load_config("config.yaml")}

    run_id = start_run(db, watch_id or "*", "enrich")
    ok, failed, rate_limit_hit = _run_loop(db, pending, watches, model)

    if rate_limit_hit:
        run_error = "rate-limit hit, run aborted"
    elif failed:
        run_error = f"{failed} failures"
    else:
        run_error = None
    finish_run(db, run_id, ads_processed=ok + failed, ads_new=ok, error=run_error)

    if rate_limit_hit:
        print(f"\n=== Stopped early: {ok} ok, {failed} failed ===", file=sys.stderr)
        return 2

    print(f"\n=== Enrich summary: {ok} ok, {failed} failed ===")
    return 1 if failed and not ok else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enrich ads via claude CLI")
    parser.add_argument("--watch", help="Limit to a single watch_id")
    parser.add_argument("--limit", type=int, default=50, help="Max ads per run")
    parser.add_argument("--model", default="opus", help="claude model: opus or haiku")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Re-enrich all active ads (not just unenriched ones). Use after schema changes.",
    )
    args = parser.parse_args()
    sys.exit(enrich(args.watch, args.limit, args.model, reset=args.reset))
