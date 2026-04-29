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


def upsert_ads(
    db: Client, watch_id: str, ads: list[FetchedAd], category_label: Optional[str] = None
) -> tuple[int, int]:
    """Upsert chaque annonce. Si le prix a changé, on log dans price_history.
    Retourne (new_count, updated_count)."""
    now = datetime.now(timezone.utc).isoformat()
    new_count = 0
    updated_count = 0

    if not ads:
        return 0, 0

    # On récupère les annonces déjà connues (pour comparer les prix)
    ad_ids = [a.id for a in ads]
    existing = (
        db.table("ads")
        .select("id, current_price")
        .in_("id", ad_ids)
        .execute()
    )
    known_prices: dict[int, Optional[float]] = {
        row["id"]: row["current_price"] for row in existing.data
    }

    rows_to_upsert: list[dict] = []
    price_history_rows: list[dict] = []

    for a in ads:
        is_new = a.id not in known_prices
        old_price = known_prices.get(a.id)

        row: dict = {
            "id": a.id,
            "watch_id": watch_id,
            # auto_category_label (depuis classify_vtt) override le label du watch
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
            new_count += 1
        else:
            updated_count += 1

        rows_to_upsert.append(row)

        # Log historique : ligne à chaque first_seen ou changement de prix
        price_changed = (
            a.price is not None
            and (is_new or (old_price is not None and float(old_price) != a.price))
        )
        if price_changed:
            price_history_rows.append(
                {"ad_id": a.id, "price": a.price, "seen_at": now}
            )

    # default_to_null=False : pour les upserts qui matchent une ligne existante,
    # les colonnes non envoyées (ex: first_seen_at sur un update) sont laissees
    # telles quelles plutot que d'etre remises a NULL. Sans ça, un update casse
    # le not-null constraint sur first_seen_at.
    db.table("ads").upsert(rows_to_upsert, default_to_null=False).execute()
    if price_history_rows:
        db.table("price_history").insert(price_history_rows).execute()

    return new_count, updated_count


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
    valid_cats = {"xc", "trail", "all_mountain", "enduro", "dh", "dirt"}
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
