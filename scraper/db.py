"""Couche d'accès Supabase. Le scraper utilise la service_role key pour
bypasser RLS (lecture/écriture totales)."""

import os
from datetime import datetime, timezone
from typing import Optional

from dotenv import load_dotenv
from supabase import Client, create_client

from .fetcher import FetchedAd

load_dotenv()


def get_client() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY manquant dans .env"
        )
    return create_client(url, key)


def upsert_ads(
    db: Client, watch_id: str, ads: list[FetchedAd]
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
            "subject": a.subject,
            "body": a.body,
            "url": a.url,
            "image_url": a.image,
            "city": a.city,
            "zipcode": a.zipcode,
            "category_id": a.category_id,
            "category_name": a.category_name,
            "current_price": a.price,
            "first_publication": a.first_publication_date,
            "last_seen_at": now,
            "is_active": True,
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

    db.table("ads").upsert(rows_to_upsert).execute()
    if price_history_rows:
        db.table("price_history").insert(price_history_rows).execute()

    return new_count, updated_count


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


def update_enrichment(
    db: Client,
    ad_id: int,
    enriched: dict,
    model: str,
) -> None:
    """Met à jour les colonnes enriched_* d'une annonce."""
    db.table("ads").update(
        {
            "brand": enriched.get("brand"),
            "model": enriched.get("model"),
            "year": enriched.get("year"),
            "frame_material": enriched.get("frame_material"),
            "wheel_size": enriched.get("wheel_size"),
            "electric": enriched.get("electric"),
            "size_label": enriched.get("size_label"),
            "condition_score": enriched.get("condition_score"),
            "estimated_market_eur": enriched.get("estimated_market_eur"),
            "deal_score": enriched.get("deal_score"),
            "reasoning": enriched.get("reasoning"),
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
