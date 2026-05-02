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
import re
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
        # Categorie d'usage VTT (ne s'applique qu'aux annonces VTT). NULL si
        # impossible a determiner depuis l'annonce.
        "vtt_category": {
            "type": ["string", "null"],
            "enum": ["xc", "all_mountain", "enduro", "dh", "dirt", None],
        },
        "condition_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "estimated_market_eur": {"type": "number"},
        "deal_score": {"type": "integer", "minimum": 0, "maximum": 100},
        # Reasoning bornee a ~500 chars pour limiter les tokens output
        "reasoning": {"type": "string", "maxLength": 500},
        "pros": {
            "type": "array",
            "items": {"type": "string", "maxLength": 80},
            "minItems": 0,
            "maxItems": 4,
        },
        "cons": {
            "type": "array",
            "items": {"type": "string", "maxLength": 80},
            "minItems": 0,
            "maxItems": 4,
        },
    },
    "required": [
        "brand", "model", "year", "electric",
        "condition_score", "estimated_market_eur", "deal_score",
        "reasoning", "pros", "cons",
    ],
}


# Regles VTT communes (decote, penalites, classification). Compactees pour
# minimiser les tokens d'input - Claude connait deja le marche, on lui rappelle
# juste les criteres a appliquer.
_VTT_DECOTE_RULES = """
DECOTE VTT (% du prix neuf):
<4 ans:50-70% | 4-7 ans:25-40% | 8-12 ans:12-22% (obsolescence techno) | >12 ans:5-15%

PENALITES (cumulables):
26" (avant ~2015): -30% | suspensions axe 9mm/pas-Boost: -20%
cassette 9V/10V: -10% | cadre alu raye: -10 a -20%

CLASSIFICATION vtt_category (mm debattement):
xc:100-120 | all_mountain:120-150 (= ancien "trail") | enduro:150-170
dh:180-200 (incl. freeride) | dirt:hardtail jump/pumptrack
=> null si impossible a trancher

NB: si modele < 2018, ne PAS surestimer la cote.
"""


DOMAIN_INTROS = {
    "vtt_enduro": (
        "Expert marche VTT enduro/AM d'occasion FR (cote reelle LBC, pas Argus)."
        + _VTT_DECOTE_RULES
    ),
    "vtt_dh": (
        "Expert marche VTT DH/freeride d'occasion FR (cote reelle LBC). "
        "VTT DH = double couronne 170-200mm av, gros amorti ar, plateau unique, "
        "4 pistons, pneus carcasse DH, slack 63-64°, usage piste."
        + _VTT_DECOTE_RULES
    ),
    "voiture": (
        "Tu es un expert du marche automobile d'occasion en France, specialise dans "
        "les voitures familiales (ludospaces, monospaces compacts/grands 7 places). "
        "Modeles courants : Citroen Berlingo, Peugeot Partner Tepee/Rifter, Renault Kangoo, "
        "Fiat Doblo, VW Caddy, Opel Combo/Combo Life, Dacia Dokker, Dacia Jogger, Ford "
        "Tourneo Connect/Courier, Toyota Proace City Verso, VW Touran/Sharan, Renault "
        "Scenic/Grand Scenic/Espace, Citroen C4 SpaceTourer, Grand C4 Picasso, Ford S-Max/"
        "Galaxy, Seat Alhambra, Kia Carens. "
        "\n\n"
        "REGLES DE DECOTE AUTO (a appliquer rigoureusement) :\n"
        "- modele < 3 ans : prix occasion ~ 70-85% du neuf\n"
        "- modele 3-6 ans : ~ 45-65% du neuf\n"
        "- modele 7-10 ans : ~ 25-40% du neuf\n"
        "- modele 11-15 ans : ~ 10-22% du neuf\n"
        "- > 15 ans : ~ 5-12% du neuf (collection ou epave)\n"
        "\n"
        "PENALITES SPECIFIQUES :\n"
        "- Diesel < Crit'Air 2 (avant 2011) : -25% (interdit zones ZFE Paris/Lyon/etc.)\n"
        "- Crit'Air 3 diesel (2011-2015) : -15% (interdiction progressive)\n"
        "- Kilometrage > 200k km : -20%, > 250k km : -35%\n"
        "- Boite auto sur petites cylindrees (<1.4) : souvent decote (couteux a entretenir)\n"
        "- CT a refaire / contre-visite mentionnee : -10 a -25% selon ampleur\n"
        "- Courroie de distri non refaite a >100k km : -15% (cout 600-1200 EUR)\n"
        "- Vehicule professionnel (taxi/VTC) : -15 a -25% supplementaires\n"
        "\n"
        "BONUS :\n"
        "- Essence/hybride/electrique recent : valorisation +10-20% vs equivalent diesel\n"
        "- Carnet d'entretien complet, factures : +5-10%\n"
        "- BVA recente sur grosse cylindrée (>1.6) : neutre/+5%\n"
        "\n"
        "Donne un deal_score qui reflete UNIQUEMENT l'ecart prix vs cote marche reelle "
        "(ce a quoi ce vehicule precis se vend reellement sur LBC, pas l'Argus theorique)."
    ),
    "moto": (
        "Tu es un expert du marche moto d'occasion en France, specialise dans les "
        "cylindrees moyennes (125-500cc) accessibles en permis A2 ou A. "
        "Segments : roadster (MT-07, CB500F, SV650, Z650, Duke 390), trail/aventure "
        "(V-Strom 250/650, NC750X, Tracer 700, F750GS), sportive (R3, Ninja 400/650, "
        "RS660), custom (Vulcan S, Rebel 500, Bolt), supermotard (Husqvarna 701, "
        "KTM 690 SMC), enduro/cross route-legaux (CRF300L, KTM EXC). "
        "\n\n"
        "REGLES DE DECOTE MOTO :\n"
        "- modele < 3 ans : ~ 65-80% du neuf\n"
        "- modele 3-6 ans : ~ 40-60% du neuf\n"
        "- modele 7-10 ans : ~ 25-40% du neuf\n"
        "- modele 11-15 ans : ~ 12-25% du neuf\n"
        "- > 15 ans : ~ 5-15% du neuf (sauf modeles cultes : MT-07 1ere gen, SV650 carbu)\n"
        "\n"
        "PENALITES KILOMETRAGE / ENTRETIEN :\n"
        "- > 30 000 km : -10% (revisions majeures dues : soupapes, distri si applicable)\n"
        "- > 60 000 km : -25% (consommables lourds : amortisseurs, suspension)\n"
        "- Pneus a remplacer (nervures < 50%) : -100 a -300 EUR\n"
        "- Chaine + couronne en bout de course : -150 a -400 EUR\n"
        "- Plaquettes / disques avant uses : -100 a -250 EUR\n"
        "- Pas de carnet entretien : -10%\n"
        "- Carbu vs injection (avant ~2008) : decote leger sauf marche collection\n"
        "\n"
        "BONUS :\n"
        "- A2-friendly (bridable ou < 47ch d'origine) : +5-10% vs version full power\n"
        "- ABS de serie : +5% (obligatoire neuf depuis 2017 mais pas sur l'ancien)\n"
        "- 1ere main avec historique : +5-10%\n"
        "\n"
        "Donne un deal_score qui reflete UNIQUEMENT l'ecart prix vs cote marche reelle."
    ),
}


def build_prompt(ad: dict, domain: Optional[str]) -> str:
    intro = DOMAIN_INTROS.get(domain or "", "Tu es un expert du marche francais d'occasion.")
    body = (ad.get("body") or "").strip()
    if len(body) > 800:
        body = body[:800] + "..."

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

Analyse cette annonce et evalue si c'est une bonne affaire.

Titre: {ad.get("subject", "")}
Prix: {price_str} | Ville: {ad.get("city") or "?"}{attr_block}
Description: {body or "(vide)"}

ESTIME le prix de revente occasion REEL (sur LBC/Vinted/forums, pas Argus theorique).
Applique les regles de decote ci-dessus rigoureusement.

deal_score = ecart prix vs marche reel UNIQUEMENT :
0=tres cher | 30=un peu cher | 50=au marche | 70=sous marche -15 a -30% | 90+=>-30%

REGLE: ne baisse JAMAIS le deal_score pour cause d'arnaque suspectee. Prix bas vs
marche => score haut, point. Les doutes vont dans `cons`, pas dans le score.

condition_score: 0=HS | 50=usure visible | 80=bon etat | 95+=quasi neuf.

Sois concis. Reponds en JSON via le schema:
- reasoning: 2-3 phrases (max ~80 mots), explique le score + situe le modele.
- pros: 2-4 points concrets et brefs (max ~10 mots/item).
- cons: 2-4 points concrets et brefs (max ~10 mots/item).
"""


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


_SUBJECT_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")


def _normalize_subject(s: str) -> str:
    """Normalise le subject pour detecter les doublons : lowercase, retire
    ponctuation, espaces, mais aussi les 'marketing tags' qui distinguent les
    republications (| Garanti 1 an, | Reconditionne, | 14 jours, etc).
    On coupe au 1er separateur '|' s'il existe (commun chez les pros)."""
    if not s:
        return ""
    cut = s.split("|")[0]  # garde la partie avant le 1er |
    return _SUBJECT_NORMALIZE_RE.sub("", cut.lower())


def _find_duplicate(db, ad: dict) -> Optional[dict]:
    """Cherche en base une annonce DEJA enrichie qui ressemble a `ad` :
    meme prix + meme ville + subject normalise identique. Si trouvee, on
    pourra copier les enrichissements au lieu de re-appeler Claude.
    Retourne le dict de l'annonce trouvee, ou None."""
    norm = _normalize_subject(ad.get("subject") or "")
    if not norm or not ad.get("city") or ad.get("current_price") is None:
        return None
    rows = (
        db.table("ads")
        .select("id, subject, brand, model, year, frame_material, wheel_size, "
                "electric, size_label, vtt_category, condition_score, "
                "estimated_market_eur, deal_score, reasoning, pros, cons")
        .eq("city", ad["city"])
        .eq("current_price", ad["current_price"])
        .neq("id", ad["id"])
        .not_.is_("deal_score", "null")
        .limit(20)
        .execute()
        .data
    )
    for r in rows:
        if _normalize_subject(r.get("subject") or "") == norm:
            return r
    return None


def _copy_enrichment(db, target_ad_id: int, source: dict, model: str) -> None:
    """Copie les champs enrichis d'une annonce source vers la target. Sert quand
    on detecte un doublon : pas la peine de cramer Claude, on reprend le travail."""
    payload = {
        "brand": source.get("brand"),
        "model": source.get("model"),
        "year": source.get("year"),
        "frame_material": source.get("frame_material"),
        "wheel_size": source.get("wheel_size"),
        "electric": source.get("electric"),
        "size_label": source.get("size_label"),
        "vtt_category": source.get("vtt_category"),
        "condition_score": source.get("condition_score"),
        "estimated_market_eur": source.get("estimated_market_eur"),
        "deal_score": source.get("deal_score"),
        "reasoning": source.get("reasoning"),
        "pros": source.get("pros"),
        "cons": source.get("cons"),
    }
    update_enrichment(db, target_ad_id, payload, model=f"{model}+dedup")


def _process_one(db, ad: dict, watches: dict, model: str) -> bool:
    """Enrichit une annonce. Retourne True si succes, False si echec."""
    # Court-circuit anti-doublon : si une annonce identique (subject normalise
    # + meme prix + meme ville) est deja enrichie, on copie ses champs au lieu
    # de relancer Claude. Cas frequent : revendeur pro qui republie 3x la meme
    # annonce avec des angles marketing differents ("Garanti", "Livraison", etc).
    try:
        dup = _find_duplicate(db, ad)
    except Exception as e:
        print(f"  (dedup check failed for {ad['id']}: {e})", file=sys.stderr)
        dup = None
    if dup:
        _copy_enrichment(db, ad["id"], dup, model)
        print(f"  -> DEDUP from ad {dup['id']} (deal_score={dup.get('deal_score')})")
        return True

    watch = watches.get(ad["watch_id"])
    # Pour les VTT, le category_label de l'annonce ('VTT enduro' ou 'VTT DH')
    # surclasse l'enrichment_domain du watch — un seul watch large peut produire
    # les deux categories selon classify_vtt().
    cat_label = (ad.get("category_label") or "").strip()
    if cat_label == "VTT DH":
        domain = "vtt_dh"
    elif cat_label == "VTT enduro":
        domain = "vtt_enduro"
    else:
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


class _LoopState:
    """Etat mute partage entre _run_loop et _handle_future_result. Sert a eviter
    de passer 6 args + retourner 6 valeurs. Pas de logique : juste des champs."""
    def __init__(self) -> None:
        self.ok = 0
        self.failed = 0
        self.ok_ids: list[int] = []
        self.completed = 0
        self.last_results: list[bool] = []  # fenetre glissante rate-limit


def _handle_future_result(
    state: _LoopState,
    ad: dict,
    success: bool,
    total: int,
    prefix: str,
) -> None:
    """Met a jour `state` avec le resultat d'un future et log la ligne."""
    state.completed += 1
    status = "OK" if success else "FAIL"
    print(f"{prefix}[{state.completed}/{total}] [{ad['id']}] {status} | {ad['subject'][:60]}")
    if success:
        state.ok += 1
        state.ok_ids.append(ad["id"])
    else:
        state.failed += 1
    state.last_results.append(success)
    if len(state.last_results) > _CONSECUTIVE_FAILURE_LIMIT:
        state.last_results.pop(0)


def _is_rate_limited(state: _LoopState) -> bool:
    """Renvoie True si la fenetre glissante des derniers resultats est entierement
    en echec (signale probable quota Claude epuise)."""
    return (
        len(state.last_results) == _CONSECUTIVE_FAILURE_LIMIT
        and not any(state.last_results)
    )


def _run_loop(
    db, pending: list, watches: dict, model: str, prefix: str = "",
    parallelism: int = 3,
) -> tuple[int, int, bool, list[int]]:
    """Boucle principale d'enrichissement, parallelisee.

    On lance jusqu'a `parallelism` subprocess Claude CLI en parallele : chaque
    appel CLI a un overhead boot ~3s, donc paralleliser donne un gain immediat
    x3-x4. Claude API supporte la concurrence; Supabase aussi.

    Le detecteur de rate-limit utilise une fenetre glissante des derniers
    resultats finis (parallelisme rend la notion de "consecutif" non lineaire).

    Retourne (ok, failed, rate_limit_hit, ok_ids)."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    state = _LoopState()
    total = len(pending)
    rate_limit_hit = False

    with ThreadPoolExecutor(max_workers=parallelism) as pool:
        future_to_ad = {
            pool.submit(_process_one, db, ad, watches, model): ad
            for ad in pending
        }
        for future in as_completed(future_to_ad):
            ad = future_to_ad[future]
            try:
                success = future.result()
            except Exception as e:
                print(f"  WORKER CRASH on ad {ad['id']}: {e}", file=sys.stderr)
                success = False

            _handle_future_result(state, ad, success, total, prefix)

            if _is_rate_limited(state):
                print(
                    f"\n!!! {_CONSECUTIVE_FAILURE_LIMIT} echecs sur les derniers "
                    f"resultats - probable rate-limit Claude (quota {model} "
                    f"epuise). Arret du run.",
                    file=sys.stderr,
                )
                rate_limit_hit = True
                for f in future_to_ad:
                    if not f.done():
                        f.cancel()
                break

    if rate_limit_hit:
        _reset_failed_burst(db, pending, state.completed, _CONSECUTIVE_FAILURE_LIMIT)

    return state.ok, state.failed, rate_limit_hit, state.ok_ids


def enrich(
    watch_id: Optional[str] = None,
    limit: int = 50,
    model: str = "opus",
    reset: bool = False,
    parallelism: int = 3,
) -> int:
    db = get_client()
    if reset:
        pending = fetch_active_ads(db, watch_id=watch_id, limit=limit)
        print(f"[--reset] Re-enriching {len(pending)} active ads (model={model}, parallelism={parallelism})")
    else:
        pending = fetch_unenriched_ads(db, watch_id=watch_id, limit=limit)
        print(f"Found {len(pending)} unenriched ads (model={model}, parallelism={parallelism})")

    if not pending:
        return 0

    from .config import load_config
    watches = {w.id: w for w in load_config("config.yaml")}

    run_id = start_run(db, watch_id or "*", "enrich")
    ok, failed, rate_limit_hit, _ = _run_loop(
        db, pending, watches, model, parallelism=parallelism
    )

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


def enrich_hybrid(
    watch_id: Optional[str] = None,
    limit: int = 50,
    reset: bool = False,
    refine_threshold: int = 60,
) -> int:
    """Mode hybride : pass Haiku rapide sur tout, puis pass Opus de raffinement
    sur les annonces dont le deal_score Haiku >= refine_threshold.

    Retour : 0 = ok, 1 = quelques echecs, 2 = rate-limit hit."""
    db = get_client()
    if reset:
        pending = fetch_active_ads(db, watch_id=watch_id, limit=limit)
        print(f"[hybrid --reset] {len(pending)} active ads to process")
    else:
        pending = fetch_unenriched_ads(db, watch_id=watch_id, limit=limit)
        print(f"[hybrid] {len(pending)} unenriched ads to process")

    if not pending:
        return 0

    from .config import load_config
    watches = {w.id: w for w in load_config("config.yaml")}

    # === Pass 1 : Haiku sur tout ===
    print(f"\n>>> PASS 1 / Haiku ({len(pending)} ads)")
    run_id_1 = start_run(db, watch_id or "*", "enrich")
    ok1, failed1, rate1, ok_ids = _run_loop(
        db, pending, watches, model="haiku", prefix="[H1] ",
    )
    finish_run(
        db, run_id_1, ads_processed=ok1 + failed1, ads_new=ok1,
        error="rate-limit hit (haiku)" if rate1 else (f"{failed1} failures" if failed1 else None),
    )
    if rate1:
        print(f"\n=== Hybrid aborted at pass 1: {ok1} ok, {failed1} failed ===", file=sys.stderr)
        return 2
    if not ok_ids:
        print("\n=== No successful Haiku analysis, nothing to refine ===")
        return 1 if failed1 else 0

    # === Pass 2 : Opus uniquement sur les annonces deal_score >= refine_threshold ===
    refresh = (
        db.table("ads")
        .select("*")
        .in_("id", ok_ids)
        .gte("deal_score", refine_threshold)
        .execute()
    )
    to_refine = refresh.data
    print(
        f"\n>>> PASS 2 / Opus refinement ({len(to_refine)}/{len(ok_ids)} ads "
        f"with deal_score >= {refine_threshold})"
    )

    if not to_refine:
        print(f"\n=== Hybrid done: {ok1} Haiku, 0 promoted to Opus ===")
        return 0

    run_id_2 = start_run(db, watch_id or "*", "enrich")
    ok2, failed2, rate2, _ = _run_loop(
        db, to_refine, watches, model="opus", prefix="[O2] ",
    )
    finish_run(
        db, run_id_2, ads_processed=ok2 + failed2, ads_new=ok2,
        error="rate-limit hit (opus)" if rate2 else (f"{failed2} failures" if failed2 else None),
    )

    print(
        f"\n=== Hybrid done: {ok1} Haiku passes, {ok2} Opus refinements"
        + (f", {failed2} Opus failures" if failed2 else "")
        + (" (Opus rate-limited)" if rate2 else "")
        + " ==="
    )
    return 2 if rate2 else (1 if (failed1 or failed2) else 0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enrich ads via claude CLI")
    parser.add_argument("--watch", help="Limit to a single watch_id")
    parser.add_argument("--limit", type=int, default=50, help="Max ads per run")
    parser.add_argument("--model", default="opus", help="claude model: opus | sonnet | haiku (default: opus, le plus precis)")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Re-enrich all active ads (not just unenriched ones). Use after schema changes.",
    )
    parser.add_argument(
        "--hybrid",
        action="store_true",
        help="Hybrid mode: Haiku on everything, then Opus only on deal_score >= --refine-threshold.",
    )
    parser.add_argument(
        "--refine-threshold",
        type=int,
        default=60,
        help="Min deal_score from Haiku to trigger Opus refinement (default: 60).",
    )
    parser.add_argument(
        "--parallelism",
        type=int,
        default=3,
        help="Nb de subprocess Claude CLI en parallele (default: 3, gain ~x3-x4 sur l'overhead boot CLI)",
    )
    args = parser.parse_args()
    if args.hybrid:
        sys.exit(enrich_hybrid(
            args.watch, args.limit,
            reset=args.reset, refine_threshold=args.refine_threshold,
        ))
    sys.exit(enrich(
        args.watch, args.limit, args.model,
        reset=args.reset, parallelism=args.parallelism,
    ))
