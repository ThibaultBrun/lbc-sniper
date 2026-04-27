from dataclasses import dataclass
from typing import Optional

import lbc

from .config import Watch


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
    first_publication_date: Optional[str]
    category_id: Optional[str]
    category_name: Optional[str]
    attributes: dict[str, str]


def _ad_to_fetched(ad: lbc.Ad) -> FetchedAd:
    attrs: dict[str, str] = {}
    for a in ad.attributes or []:
        if a.key and a.value_label:
            attrs[a.key] = a.value_label
    return FetchedAd(
        id=ad.id,
        subject=ad.subject,
        body=ad.body,
        price=ad.price,
        url=ad.url,
        image=(ad.images[0] if ad.images else None),
        city=ad.location.city_label if ad.location else None,
        zipcode=ad.location.zipcode if ad.location else None,
        first_publication_date=ad.first_publication_date,
        category_id=ad.category_id,
        category_name=ad.category_name,
        attributes=attrs,
    )


def fetch_watch(client: lbc.Client, watch: Watch) -> list[FetchedAd]:
    if watch.location.lat is None or watch.location.lng is None:
        raise ValueError(
            f"Watch '{watch.id}' is missing lat/lng for '{watch.location.city}'"
        )

    city = lbc.City(
        lat=watch.location.lat,
        lng=watch.location.lng,
        radius=watch.location.radius_km * 1000,
        city=watch.location.city,
    )

    try:
        category = lbc.Category[watch.category]
    except KeyError as e:
        raise ValueError(f"Unknown lbc.Category: {watch.category}") from e

    kwargs: dict = {}
    if watch.price_max is not None:
        kwargs["price"] = (0, watch.price_max)

    result = client.search(
        text=watch.text,
        category=category,
        locations=[city],
        limit=watch.limit,
        sort=lbc.Sort.NEWEST,
        **kwargs,
    )

    fetched = [_ad_to_fetched(ad) for ad in result.ads]

    if watch.accept_category_ids:
        allowed = set(watch.accept_category_ids)
        fetched = [a for a in fetched if a.category_id in allowed]

    return fetched
