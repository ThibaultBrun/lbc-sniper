import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import lbc

from .config import AttributeFilter, Watch


_NUM_RE = re.compile(r"-?\d+")


def _extract_first_int(s: Optional[str]) -> Optional[int]:
    """Extrait le premier entier d'une string LBC type '300 cm²', '4800 km', '2011'."""
    if not s:
        return None
    m = _NUM_RE.search(s)
    return int(m.group(0)) if m else None


def _ad_passes_attribute_filters(
    attrs: dict[str, str], filters: dict[str, AttributeFilter]
) -> bool:
    """Applique les filtres min/max si l'attribut est present. Si l'attribut
    n'est pas dans l'annonce, on garde l'annonce (on n'a pas de raison de
    rejeter sur l'absence d'info)."""
    for key, rng in filters.items():
        raw = attrs.get(key)
        val = _extract_first_int(raw)
        if val is None:
            continue
        if rng.min is not None and val < rng.min:
            return False
        if rng.max is not None and val > rng.max:
            return False
    return True


@dataclass
class FetchedAd:
    id: int
    subject: str
    body: Optional[str]
    price: Optional[float]
    url: str
    image: Optional[str]
    city: Optional[str]
    zipcode: Optional[str]
    lat: Optional[float]
    lng: Optional[float]
    first_publication_date: Optional[str]
    category_id: Optional[str]
    category_name: Optional[str]
    attributes: dict[str, str]


def _ad_to_fetched(ad: lbc.Ad) -> FetchedAd:
    attrs: dict[str, str] = {}
    for a in ad.attributes or []:
        if a.key and a.value_label:
            attrs[a.key] = a.value_label
    loc = ad.location
    return FetchedAd(
        id=ad.id,
        subject=ad.subject,
        body=ad.body,
        price=ad.price,
        url=ad.url,
        image=(ad.images[0] if ad.images else None),
        city=loc.city_label if loc else None,
        zipcode=loc.zipcode if loc else None,
        lat=loc.lat if loc else None,
        lng=loc.lng if loc else None,
        first_publication_date=ad.first_publication_date,
        category_id=ad.category_id,
        category_name=ad.category_name,
        attributes=attrs,
    )


def _parse_lbc_date(s: Optional[str]) -> Optional[datetime]:
    """LBC renvoie soit '2026-04-29T08:48:49Z' soit '2026-04-29 08:48:49'."""
    if not s:
        return None
    try:
        if "T" in s:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def _apply_filters(fetched: list[FetchedAd], watch: Watch) -> list[FetchedAd]:
    if watch.accept_category_ids:
        allowed = set(watch.accept_category_ids)
        fetched = [a for a in fetched if a.category_id in allowed]
    if watch.attribute_filters:
        fetched = [
            a for a in fetched
            if _ad_passes_attribute_filters(a.attributes, watch.attribute_filters)
        ]
    return fetched


def fetch_watch(client: lbc.Client, watch: Watch) -> list[FetchedAd]:
    """Fetch les annonces d'un watch.

    - Si watch.incremental_hours est defini, on pagine jusqu'a tomber sur une
      annonce plus vieille que la fenetre demandee. Sinon on fait un seul
      appel avec watch.limit.
    - watch.location peut etre None (recherche France entiere)."""
    try:
        category = lbc.Category[watch.category]
    except KeyError as e:
        raise ValueError(f"Unknown lbc.Category: {watch.category}") from e

    locations = None
    if watch.location and watch.location.lat is not None and watch.location.lng is not None:
        locations = [lbc.City(
            lat=watch.location.lat,
            lng=watch.location.lng,
            radius=watch.location.radius_km * 1000,
            city=watch.location.city,
        )]

    kwargs: dict = {}
    if watch.price_max is not None:
        kwargs["price"] = (0, watch.price_max)

    if watch.incremental_hours is None:
        # Mode classique : un seul appel
        result = client.search(
            text=watch.text,
            category=category,
            locations=locations,
            limit=watch.limit,
            sort=lbc.Sort.NEWEST,
            search_in_title_only=watch.search_in_title_only,
            **kwargs,
        )
        return _apply_filters([_ad_to_fetched(ad) for ad in result.ads], watch)

    # Mode incremental : on pagine jusqu'a tomber sur une annonce plus vieille
    # que (now - incremental_hours), ou jusqu'a un cap raisonnable de pages.
    cutoff = datetime.now(timezone.utc) - timedelta(hours=watch.incremental_hours)
    all_fetched: list[FetchedAd] = []
    seen_ids: set[int] = set()
    max_pages = 20  # garde-fou (LBC autorise plus mais on n'en aura jamais besoin)

    for page in range(1, max_pages + 1):
        result = client.search(
            text=watch.text,
            category=category,
            locations=locations,
            limit=watch.limit,
            page=page,
            sort=lbc.Sort.NEWEST,
            search_in_title_only=watch.search_in_title_only,
            **kwargs,
        )
        if not result.ads:
            break

        page_fetched: list[FetchedAd] = []
        oldest_in_page: Optional[datetime] = None
        for raw_ad in result.ads:
            fa = _ad_to_fetched(raw_ad)
            if fa.id in seen_ids:
                continue
            seen_ids.add(fa.id)
            page_fetched.append(fa)
            pub = _parse_lbc_date(fa.first_publication_date)
            if pub and (oldest_in_page is None or pub < oldest_in_page):
                oldest_in_page = pub

        all_fetched.extend(page_fetched)

        # Stop si la page la plus ancienne est < cutoff
        if oldest_in_page and oldest_in_page < cutoff:
            break

    # Filtre temporel + filtres watch
    in_window = [
        a for a in all_fetched
        if (pub := _parse_lbc_date(a.first_publication_date)) is None or pub >= cutoff
    ]
    return _apply_filters(in_window, watch)
