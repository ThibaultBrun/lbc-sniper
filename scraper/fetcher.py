import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import lbc

from .config import AttributeFilter, Watch
from .vtt_models import (
    BRANDS_ENDURO_PURE,
    DH_TERMS,
    ENDURO_TERMS,
    GENERIC_DH,
    GENERIC_ENDURO,
)


_NUM_RE = re.compile(r"-?\d+")
_NORMALIZE_RE = re.compile(r"[^a-z0-9 +-]")
_WHITESPACE_RE = re.compile(r"\s+")
_ACCENTS = str.maketrans({
    "é": "e", "è": "e", "ê": "e", "ë": "e",
    "î": "i", "ï": "i",
    "ô": "o", "ö": "o",
    "û": "u", "ù": "u", "ü": "u",
    "à": "a", "â": "a", "ä": "a",
    "ç": "c",
})


def _normalize_text(s: Optional[str]) -> str:
    """Lowercase, retire accents, ne garde que [a-z0-9 +-], espaces normalises."""
    if not s:
        return ""
    s = s.lower().translate(_ACCENTS)
    s = _NORMALIZE_RE.sub(" ", s)
    return _WHITESPACE_RE.sub(" ", s).strip()


def _contains_word(haystack_padded: str, needle: str) -> bool:
    """Cherche needle comme mot/groupe-de-mots entier dans haystack_padded.
    haystack_padded doit deja avoir des espaces en debut+fin pour que les
    needles 'dh' / 'enduro' ne matchent pas a l'interieur de mots comme
    'adherence' ou 'gentleman'."""
    return f" {needle} " in haystack_padded


# Termes qui qualifient indubitablement "VTT" (montagne, off-road).
# Au moins UN de ces termes doit etre present pour qu'un nom de modele
# isole comme 'element' / 'titan' / 'capra' soit pris au serieux.
_VTT_QUALIFIERS = {
    "vtt", "vttae", "vttea", "mtb", "mountain bike", "mountainbike", "vtc",
    "tout suspendu", "all mountain", "allmountain",
    "enduro", "freeride", "downhill", "descente", "dh",
    "trail bike", "endurigide", "hardtail",
    "vae mtb", "vae vtt", "e-mtb", "emtb",
    "tout-terrain", "tout terrain",
}


def _has_vtt_qualifier(padded: str) -> bool:
    return any(_contains_word(padded, q) for q in _VTT_QUALIFIERS)


def classify_vtt(subject: str, body: Optional[str]) -> Optional[str]:
    """Cherche un signal VTT (XC, enduro, DH) dans le titre+body normalises.
    Retourne 'VTT DH', 'VTT enduro', 'VTT XC', ou None.
    Priorites :
      DH > enduro > XC (un VTT qualifie pour plusieurs = celui de plus haute priorite).

    Strategie en 2 etapes pour eviter les faux positifs :
    1. Les mots-cles 'enduro' / 'dh' / 'xc' / etc. qualifient seuls.
    2. Les noms de modeles ou marques pure-MTB ne qualifient QUE si on
       trouve aussi un signal 'vtt' / 'mtb' / 'mountain' / etc. dans le texte.
    """
    from .vtt_models import GENERIC_XC

    text = _normalize_text(f"{subject or ''} {body or ''}")
    padded = f" {text} "

    # Niveau 1 : mots-cles qui qualifient seuls (DH > enduro > XC).
    for kw in GENERIC_DH:
        if _contains_word(padded, kw):
            return "VTT DH"
    for kw in GENERIC_ENDURO:
        if _contains_word(padded, kw):
            return "VTT enduro"
    for kw in GENERIC_XC:
        if _contains_word(padded, kw):
            return "VTT XC"

    # Niveau 2 : marques 100% MTB — qualifient SEULES (pas besoin de 'vtt').
    for brand in BRANDS_ENDURO_PURE:
        if _contains_word(padded, brand):
            return "VTT enduro"

    # Niveau 3 : nom de modele tout seul (potentiellement ambigu : 'titan',
    # 'element', 'capra'). Demande un qualifier 'vtt'/'mtb'/etc. dans le texte.
    if not _has_vtt_qualifier(padded):
        return None

    for term in DH_TERMS:
        if _contains_word(padded, term):
            return "VTT DH"
    for term in ENDURO_TERMS:
        if _contains_word(padded, term):
            return "VTT enduro"
    return None


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
    # Classification facultative (calculee par classify_vtt() si watch.auto_classify_vtt).
    # Override le watch.category_label au moment de l'upsert.
    auto_category_label: Optional[str] = None


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
    if watch.auto_classify_vtt:
        kept: list[FetchedAd] = []
        for a in fetched:
            label = classify_vtt(a.subject, a.body)
            if label is None:
                continue
            a.auto_category_label = label
            kept.append(a)
        fetched = kept
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
