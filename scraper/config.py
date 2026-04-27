from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class WatchLocation:
    city: str
    radius_km: int
    lat: Optional[float] = None
    lng: Optional[float] = None


@dataclass
class Watch:
    id: str
    label: str
    category: str
    text: Optional[str]
    location: WatchLocation
    price_max: Optional[int]
    limit: int
    accept_category_ids: Optional[list[str]] = None
    enrichment_domain: Optional[str] = None  # ex: "vtt", utilisé dans le prompt


def load_config(path: Path | str = "config.yaml") -> list[Watch]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    watches = []
    for w in raw["watches"]:
        loc = w["location"]
        watches.append(
            Watch(
                id=w["id"],
                label=w["label"],
                category=w["category"],
                text=w.get("text"),
                location=WatchLocation(
                    city=loc["city"],
                    radius_km=loc["radius_km"],
                    lat=loc.get("lat"),
                    lng=loc.get("lng"),
                ),
                price_max=w.get("price_max"),
                limit=int(w.get("limit", 100)),
                accept_category_ids=(
                    [str(c) for c in w["accept_category_ids"]]
                    if w.get("accept_category_ids")
                    else None
                ),
                enrichment_domain=w.get("enrichment_domain"),
            )
        )
    return watches
