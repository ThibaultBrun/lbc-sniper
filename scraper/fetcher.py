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


# Labels VTT renvoyes par classify_vtt() (= valeurs de category_label en DB).
LABEL_VTT_DH = "VTT DH"
LABEL_VTT_ENDURO = "VTT enduro"
LABEL_VTT_XC = "VTT XC"
LABEL_VTT_DIRT = "VTT dirt"


def _match_first_keyword(padded: str, keywords, label: str) -> Optional[str]:
    """Si `padded` contient un mot-cle de `keywords`, retourne `label`. Sinon None."""
    for kw in keywords:
        if _contains_word(padded, kw):
            return label
    return None


def classify_vtt(subject: str, body: Optional[str]) -> Optional[str]:
    """Cherche un signal VTT (XC, enduro, DH, dirt) dans le titre+body normalises.
    Retourne 'VTT DH', 'VTT enduro', 'VTT XC', 'VTT dirt', ou None.
    Priorites :
      dirt > DH > enduro > XC (un velo qualifie pour plusieurs = plus haute priorite).
      Dirt en premier car ce sont des hardtails specifiques, pas confondables avec enduro/DH.

    Strategie en 2 etapes pour eviter les faux positifs :
    1. Les mots-cles 'enduro' / 'dh' / 'dirt' / 'xc' / etc. qualifient seuls.
    2. Les noms de modeles ou marques pure-MTB ne qualifient QUE si on
       trouve aussi un signal 'vtt' / 'mtb' / 'mountain' / etc. dans le texte.
    """
    from .vtt_models import GENERIC_XC, GENERIC_DIRT, MODELS_UNAMBIGUOUS_ENDURO, EXCLUDE_TERMS

    text = _normalize_text(f"{subject or ''} {body or ''}")
    padded = f" {text} "

    # Niveau 0 (blacklist) : si l'annonce contient un terme excluant
    # (velo route, lot de plusieurs velos, triathlon, draisienne, etc.) on
    # rejette immediatement, peu importe les autres matches positifs.
    for kw in EXCLUDE_TERMS:
        if _contains_word(padded, kw):
            return None

    # Niveau 1 : mots-cles generiques qui qualifient seuls. Ordre = priorite.
    generic_table = (
        (GENERIC_DIRT, LABEL_VTT_DIRT),
        (GENERIC_DH, LABEL_VTT_DH),
        (GENERIC_ENDURO, LABEL_VTT_ENDURO),
        (GENERIC_XC, LABEL_VTT_XC),
    )
    for keywords, label in generic_table:
        match = _match_first_keyword(padded, keywords, label)
        if match:
            return match

    # Niveau 2 : marques 100% MTB qualifient seules (pas besoin de 'vtt').
    if _match_first_keyword(padded, BRANDS_ENDURO_PURE, LABEL_VTT_ENDURO):
        return LABEL_VTT_ENDURO

    # Niveau 2.5 : modeles VTT enduro/AM tellement specifiques qu'ils qualifient
    # seuls (Orbea Rallon, Trek Slash, etc.). Resout les annonces type
    # "Orbea Rallon M10" qui n'ont ni 'vtt' ni 'enduro' explicite mais sont
    # incontestablement des VTT enduro.
    if _match_first_keyword(padded, MODELS_UNAMBIGUOUS_ENDURO, LABEL_VTT_ENDURO):
        return LABEL_VTT_ENDURO

    # Niveau 3 : modele potentiellement ambigu ('titan', 'element').
    # Demande un qualifier 'vtt'/'mtb'/etc. dans le texte.
    if not _has_vtt_qualifier(padded):
        return None

    ambiguous_table = (
        (DH_TERMS, LABEL_VTT_DH),
        (ENDURO_TERMS, LABEL_VTT_ENDURO),
    )
    for terms, label in ambiguous_table:
        match = _match_first_keyword(padded, terms, label)
        if match:
            return match
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


# Resolution Europe/Paris : sur Windows, zoneinfo n'a pas la base IANA par
# defaut. On force le chargement via le package `tzdata` (dans requirements.txt).
# Si l'import echoue (env exotique), fallback offset fixe +1h (heure d'hiver
# Paris) - precision suffisante pour notre usage de cutoff a +/-1h.
try:
    import tzdata  # noqa: F401
    from zoneinfo import ZoneInfo
    _PARIS_TZ = ZoneInfo("Europe/Paris")
except Exception:  # pragma: no cover
    _PARIS_TZ = timezone(timedelta(hours=2))  # fallback CEST par defaut


def _parse_lbc_date(s: Optional[str]) -> Optional[datetime]:
    """LBC renvoie soit '2026-04-29T08:48:49Z' (UTC explicite) soit
    '2026-04-29 08:48:49' (heure locale PARIS, sans timezone).

    Bug constate : si on parse le 2e format en UTC, on ajoute un decalage de
    +2h en CEST (ete) ou +1h en CET (hiver) -> les annonces apparaissent dans
    le "futur" et le filtre cutoff est casse. On interprete donc explicitement
    en Europe/Paris (DST gere automatiquement par zoneinfo+tzdata)."""
    if not s:
        return None
    try:
        if "T" in s:
            return datetime.fromisoformat(s.replace("Z", "+00:00"))
        naive = datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
        return naive.replace(tzinfo=_PARIS_TZ).astimezone(timezone.utc)
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


def _build_search_kwargs(watch: Watch) -> dict:
    """Construit les kwargs communs aux appels client.search() pour un watch."""
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

    kwargs: dict = {
        "text": watch.text,
        "category": category,
        "locations": locations,
        "limit": watch.limit,
        "sort": lbc.Sort.NEWEST,
        "search_in_title_only": watch.search_in_title_only,
    }
    if watch.price_max is not None:
        kwargs["price"] = (0, watch.price_max)
    return kwargs


def _fetch_paginated(client: lbc.Client, watch: Watch) -> list[FetchedAd]:
    """Pagine LBC pour ramener les annonces publiees dans les
    `watch.incremental_hours` dernieres heures.

    ATTENTION : LBC ne trie PAS strictement par NEWEST. Il intercale des
    annonces "boostees" (republiees, pro, mises en avant) qui peuvent etre
    tres anciennes (100+ jours) dans des pages recentes. Donc on ne peut pas
    s'arreter sur "la plus vieille de la page > cutoff" sans rater massivement.

    Strategie : on continue tant que la page courante contient au moins
    `MIN_RECENT_PER_PAGE` ads dans la fenetre. Si une page entiere n'a
    que des ads vieilles -> on a quitte la zone des recentes, on stoppe.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=watch.incremental_hours or 24)
    base_kwargs = _build_search_kwargs(watch)
    all_fetched: list[FetchedAd] = []
    seen_ids: set[int] = set()
    max_pages = 20  # garde-fou
    min_recent_per_page = 2

    for page in range(1, max_pages + 1):
        result = client.search(page=page, **base_kwargs)
        if not result.ads:
            break

        recent_in_page = _process_page(result.ads, seen_ids, all_fetched, cutoff)

        # Stop si la page n'a (presque) plus d'annonces recentes : on est sortis
        # de la fenetre temporelle qui nous interesse.
        if page > 1 and recent_in_page < min_recent_per_page:
            break

    in_window = [
        a for a in all_fetched
        if (pub := _parse_lbc_date(a.first_publication_date)) is None or pub >= cutoff
    ]
    return in_window


def _process_page(
    raw_ads: list,
    seen_ids: set[int],
    all_fetched: list[FetchedAd],
    cutoff: datetime,
) -> int:
    """Convertit les ads brutes de la page, dedup, append a all_fetched.
    Retourne le nombre d'ads de la page qui sont dans la fenetre [cutoff, now]."""
    recent = 0
    for raw_ad in raw_ads:
        fa = _ad_to_fetched(raw_ad)
        if fa.id in seen_ids:
            continue
        seen_ids.add(fa.id)
        all_fetched.append(fa)
        pub = _parse_lbc_date(fa.first_publication_date)
        if pub and pub >= cutoff:
            recent += 1
    return recent


def fetch_watch(client: lbc.Client, watch: Watch) -> list[FetchedAd]:
    """Fetch les annonces d'un watch.

    - Si `watch.incremental_hours` est defini, on pagine pour ramener TOUTES
      les annonces publiees dans cette fenetre temporelle (logique deportee
      dans `_fetch_paginated`).
    - Sinon, un seul appel avec `watch.limit`.
    - `watch.location` peut etre None (recherche France entiere).
    """
    if watch.incremental_hours is None:
        result = client.search(**_build_search_kwargs(watch))
        return _apply_filters([_ad_to_fetched(ad) for ad in result.ads], watch)

    return _apply_filters(_fetch_paginated(client, watch), watch)
