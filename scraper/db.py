"""Couche d'accès Supabase. Le scraper utilise la service_role key pour
bypasser RLS (lecture/écriture totales)."""

import os
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from dotenv import load_dotenv
from supabase import Client, create_client

from .fetcher import FetchedAd

load_dotenv()


_NUM_RE = re.compile(r"-?\d+")


def _first_int(s: Optional[str]) -> Optional[int]:
    if not s:
        return None
    m = _NUM_RE.search(s)
    return int(m.group(0)) if m else None


def _extract_columns(attrs: dict[str, str]) -> dict:
    """Extrait quelques attributs LBC bien connus en colonnes top-level."""
    return {
        "mileage_km": _first_int(attrs.get("mileage")),
        "fuel": attrs.get("fuel"),
        "gearbox": attrs.get("gearbox"),
        "regyear": _first_int(attrs.get("regdate")),
    }


def get_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY manquant dans .env"
        )
    return create_client(url, key)


_DEDUP_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")


def _fingerprint(subject: Optional[str], city: Optional[str], price: Optional[float]) -> Optional[str]:
    """Cle de detection des doublons : subject normalise + city + price.
    Le subject est coupe au 1er '|' (commun chez les pros qui ajoutent un tag
    marketing apres le titre : '... | Garanti 1 an' vs '... | Livraison offerte').
    Retourne None si on n'a pas assez d'info pour dedup."""
    if not subject or not city or price is None:
        return None
    cut = subject.split("|")[0]
    norm = _DEDUP_NORMALIZE_RE.sub("", cut.lower())
    if not norm:
        return None
    return f"{norm}|{city}|{int(price)}"


def _fetch_known_prices(db: Client, ad_ids: list[int]) -> dict[int, Optional[float]]:
    """Recupere les prix connus pour les ads dont l'id est deja en base.
    Sert ensuite a detecter les changements de prix pour price_history."""
    if not ad_ids:
        return {}
    res = db.table("ads").select("id, current_price").in_("id", ad_ids).execute()
    return {row["id"]: row["current_price"] for row in res.data}


def _build_existing_duplicate_map(
    db: Client, new_ads: list[FetchedAd]
) -> dict[str, list[int]]:
    """Pour chaque nouvelle ad (id non encore en base), calcule son fingerprint.
    Cherche en base les ads existantes qui partagent le meme (city, price) puis
    matche les fingerprints. Retourne les IDs actifs a desactiver si la nouvelle
    annonce doit devenir la version canonique."""
    fingerprints_to_check: dict[str, FetchedAd] = {}
    for a in new_ads:
        fp = _fingerprint(a.subject, a.city, a.price)
        if fp:
            fingerprints_to_check[fp] = a

    if not fingerprints_to_check:
        return {}

    cities = list({a.city for a in fingerprints_to_check.values() if a.city})
    prices = list({a.price for a in fingerprints_to_check.values() if a.price is not None})
    if not cities or not prices:
        return {}

    candidates = (
        db.table("ads")
        .select("id, subject, city, current_price")
        .in_("city", cities)
        .in_("current_price", prices)
        .eq("is_active", True)
        .limit(500)
        .execute()
        .data
    )
    duplicate_ids_by_fp: dict[str, list[int]] = {}
    for row in candidates:
        fp = _fingerprint(row.get("subject"), row.get("city"), row.get("current_price"))
        if fp and fp in fingerprints_to_check and row["id"] != fingerprints_to_check[fp].id:
            duplicate_ids_by_fp.setdefault(fp, []).append(row["id"])
    return duplicate_ids_by_fp


def _build_row(
    a: FetchedAd, watch_id: str, category_label: Optional[str], now: str, is_new: bool
) -> dict:
    """Serialise une FetchedAd en dict pret a etre upserted."""
    row: dict = {
        "id": a.id,
        "watch_id": watch_id,
        "category_label": a.auto_category_label or category_label,
        "subject": a.subject,
        "body": a.body,
        "url": a.url,
        "image_url": a.image,
        "city": a.city,
        "zipcode": a.zipcode,
        "ad_lat": a.lat,
        "ad_lng": a.lng,
        "category_id": a.category_id,
        "category_name": a.category_name,
        "current_price": a.price,
        "first_publication": a.first_publication_date,
        "last_seen_at": now,
        "is_active": True,
        "attributes": a.attributes or {},
        **_extract_columns(a.attributes or {}),
    }
    if is_new:
        row["first_seen_at"] = now
    return row


class _UpsertBatch:
    """Conteneur mutable des donnees a flusher en fin d'upsert_ads.
    Existe pour permettre de splitter la grosse boucle en sous-fonctions sans
    se trimballer 6 args + 6 valeurs de retour."""
    def __init__(self) -> None:
        self.rows_to_upsert: list[dict] = []
        self.price_history_rows: list[dict] = []
        self.duplicate_ids_to_deactivate: list[int] = []
        self.new_count = 0
        self.updated_count = 0
        self.deduped_count = 0


def _existing_duplicate_ids(
    a: FetchedAd, is_new: bool, duplicate_ids_by_fp: dict[str, list[int]]
) -> list[int]:
    """Si l'ad est nouvelle et matche des annonces actives existantes, retourne
    ces IDs. On garde la nouvelle annonce et on desactive les anciennes."""
    if not is_new:
        return []
    fp = _fingerprint(a.subject, a.city, a.price)
    return duplicate_ids_by_fp.get(fp, []) if fp else []


def _process_ad(
    a: FetchedAd,
    is_new: bool,
    old_price: Optional[float],
    watch_id: str,
    category_label: Optional[str],
    now: str,
    batch: _UpsertBatch,
) -> None:
    """Ajoute une ad a la batch upsert + a l'historique de prix si change."""
    batch.rows_to_upsert.append(_build_row(a, watch_id, category_label, now, is_new))
    if is_new:
        batch.new_count += 1
    else:
        batch.updated_count += 1
    price_changed = (
        a.price is not None
        and (is_new or (old_price is not None and float(old_price) != a.price))
    )
    if price_changed:
        batch.price_history_rows.append({"ad_id": a.id, "price": a.price, "seen_at": now})


def _flush_batch(db: Client, batch: _UpsertBatch, now: str) -> None:
    """Persiste tout ce qui est dans batch (upserts + price_history + dedup)."""
    if batch.rows_to_upsert:
        # default_to_null=False : sur un update, les colonnes non envoyees
        # (ex: first_seen_at) restent en place plutot que d'etre remises a NULL.
        db.table("ads").upsert(batch.rows_to_upsert, default_to_null=False).execute()
    if batch.price_history_rows:
        db.table("price_history").insert(batch.price_history_rows).execute()
    if batch.duplicate_ids_to_deactivate:
        db.table("ads").update({"is_active": False, "last_seen_at": now}).in_(
            "id", list(set(batch.duplicate_ids_to_deactivate))
        ).execute()


def upsert_ads(
    db: Client, watch_id: str, ads: list[FetchedAd], category_label: Optional[str] = None
) -> tuple[int, int]:
    """Upsert chaque annonce. Si le prix a changé, on log dans price_history.
    Retourne (new_count, updated_count).

    DEDUP : si une annonce LBC fraichement fetchee a le meme fingerprint
    (subject normalise + city + price) qu'une annonce DEJA en base avec un
    autre id, on garde la nouvelle annonce et on desactive les anciennes.
    Cas typique : revendeurs pros qui republient le meme velo avec des angles
    marketing differents.
    """
    if not ads:
        return 0, 0

    now = datetime.now(timezone.utc).isoformat()
    known_prices = _fetch_known_prices(db, [a.id for a in ads])
    new_ads = [a for a in ads if a.id not in known_prices]
    duplicate_ids_by_fp = _build_existing_duplicate_map(db, new_ads)

    batch = _UpsertBatch()
    for a in ads:
        is_new = a.id not in known_prices
        existing_duplicates = _existing_duplicate_ids(a, is_new, duplicate_ids_by_fp)
        if existing_duplicates:
            batch.deduped_count += len(existing_duplicates)
            batch.duplicate_ids_to_deactivate.extend(existing_duplicates)
        _process_ad(a, is_new, known_prices.get(a.id), watch_id, category_label, now, batch)

    _flush_batch(db, batch, now)

    if batch.deduped_count:
        print(f"  dedup: {batch.deduped_count} ancienne(s) annonce(s) desactivee(s) (meme subject+city+price)")

    return batch.new_count, batch.updated_count


def deactivate_stale_ads(
    db: Client,
    watch_id: str,
    seen_ids: list[int],
    fetch_was_complete: bool,
    grace_days: int = 3,
) -> int:
    """Désactive les annonces du watch qui ont disparu de LBC.

    Si `fetch_was_complete` (le scraper a ramené moins que la limite, donc
    la liste est exhaustive) : tout ce qui n'est pas dans seen_ids est désactivé.

    Sinon (la liste est tronquée par la limite) : on attend `grace_days` sans
    réapparaître avant de désactiver. Une annonce qui sort du top puis y revient
    n'est donc pas pénalisée.
    """
    q = (
        db.table("ads")
        .update({"is_active": False})
        .eq("watch_id", watch_id)
        .eq("is_active", True)
    )

    if seen_ids:
        # Excluant celles qui viennent d'être vues
        q = q.not_.in_("id", seen_ids)

    if not fetch_was_complete:
        # Liste tronquée → on tolère grace_days d'absence
        cutoff = (
            datetime.now(timezone.utc) - timedelta(days=grace_days)
        ).isoformat()
        q = q.lt("last_seen_at", cutoff)

    res = q.execute()
    return len(res.data)


def fetch_unenriched_ads(db: Client, watch_id: Optional[str] = None, limit: int = 100) -> list[dict]:
    """Récupère les annonces actives qui n'ont pas encore été enrichies."""
    q = (
        db.table("ads")
        .select("*")
        .is_("enriched_at", "null")
        .eq("is_active", True)
        .order("first_seen_at", desc=True)
        .limit(limit)
    )
    if watch_id:
        q = q.eq("watch_id", watch_id)
    return q.execute().data


def fetch_active_ads(db: Client, watch_id: Optional[str] = None, limit: int = 100) -> list[dict]:
    """Récupère les annonces actives, enrichies ou pas (utilisé pour --reset)."""
    q = (
        db.table("ads")
        .select("*")
        .eq("is_active", True)
        .order("first_seen_at", desc=True)
        .limit(limit)
    )
    if watch_id:
        q = q.eq("watch_id", watch_id)
    return q.execute().data


def update_enrichment(
    db: Client,
    ad_id: int,
    enriched: dict,
    model: str,
) -> None:
    """Met à jour les colonnes enriched_* d'une annonce.

    Pour vtt_category : on prefere TOUJOURS le mapping marque/modele (fiable,
    deterministe) a la classification IA. L'IA ne sert que de fallback si on
    n'a pas le couple dans le mapping.
    """
    # Import local pour eviter cycle d'import si vtt_categories est etendu
    from .vtt_categories import classify_by_model

    brand = enriched.get("brand")
    model_name = enriched.get("model")
    mapped = classify_by_model(brand, model_name)
    vtt_cat = mapped if mapped else enriched.get("vtt_category")
    # Garde-fou : valeurs valides de l'enum SQL
    valid_cats = {"xc", "all_mountain", "enduro", "dh", "dirt"}
    # Migration douce : si l'IA renvoie encore "trail" (ancienne valeur enum),
    # on remappe vers all_mountain qui les a fusionnees.
    if vtt_cat == "trail":
        vtt_cat = "all_mountain"
    if vtt_cat not in valid_cats:
        vtt_cat = None

    db.table("ads").update(
        {
            "brand": brand,
            "model": model_name,
            "year": enriched.get("year"),
            "frame_material": enriched.get("frame_material"),
            "wheel_size": enriched.get("wheel_size"),
            "electric": enriched.get("electric"),
            "size_label": enriched.get("size_label"),
            "vtt_category": vtt_cat,
            "condition_score": enriched.get("condition_score"),
            "estimated_market_eur": enriched.get("estimated_market_eur"),
            "deal_score": enriched.get("deal_score"),
            "reasoning": enriched.get("reasoning"),
            "pros": enriched.get("pros"),
            "cons": enriched.get("cons"),
            "enriched_at": datetime.now(timezone.utc).isoformat(),
            "enrich_model": model,
            "enrich_error": None,
        }
    ).eq("id", ad_id).execute()


def update_enrichment_error(db: Client, ad_id: int, error: str, model: str) -> None:
    db.table("ads").update(
        {
            "enriched_at": datetime.now(timezone.utc).isoformat(),
            "enrich_model": model,
            "enrich_error": error[:500],
        }
    ).eq("id", ad_id).execute()


def start_run(db: Client, watch_id: str, kind: str) -> int:
    res = (
        db.table("runs")
        .insert({"watch_id": watch_id, "kind": kind})
        .execute()
    )
    return res.data[0]["id"]


def finish_run(
    db: Client,
    run_id: int,
    ads_processed: int = 0,
    ads_new: int = 0,
    ads_updated: int = 0,
    error: Optional[str] = None,
) -> None:
    db.table("runs").update(
        {
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "ads_processed": ads_processed,
            "ads_new": ads_new,
            "ads_updated": ads_updated,
            "error": error,
        }
    ).eq("id", run_id).execute()
