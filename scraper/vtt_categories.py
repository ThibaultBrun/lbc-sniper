"""Mapping marque + modele -> categorie d'usage VTT.

Categories (alignees sur l'enum SQL `vtt_category`) :
- xc            : 100-120 mm, course, leger
- trail         : 120-140 mm, polyvalent leger
- all_mountain  : 140-150 mm, le couteau suisse
- enduro        : 150-170 mm, descente engagee + montee
- dh            : 180-200 mm, descente / freeride / bike-park
- dirt          : VTT dirt jump / pumptrack (rare en occasion)

La cle est une normalisation (lowercase + retire ponctuation/espaces) du
modele. Recherche par prefixe : on matche si le modele commence par la cle.
Ca permet "Specialized Stumpjumper Comp Carbon" de matcher "stumpjumper".

Liste batie a partir des modeles courants 2018-2026 sur LBC France.
Couvre ~80% du volume VTT enduro/AM/DH (le reste tombera sur le fallback IA).
"""

import re
from typing import Optional

# Type alias
VttCategory = str  # "xc" | "trail" | "all_mountain" | "enduro" | "dh" | "dirt"


def _norm(s: str) -> str:
    """Normalise pour le matching : lowercase, retire ponctuation/espaces."""
    if not s:
        return ""
    return re.sub(r"[^a-z0-9]+", "", s.lower())


# ----------------------------------------------------------------------------
# MAPPING
# ----------------------------------------------------------------------------
# Format : (cle_normalisee_modele, categorie)
# La premiere entree qui matche par prefixe gagne. Donc on met les modeles les
# plus specifiques en premier dans la marque.

# Marques 100% / quasi-100% specialisees : tous leurs modeles sont dans la
# meme categorie, on les mappe a la marque entiere.
BRAND_DEFAULTS: dict[str, VttCategory] = {
    "yt": "enduro",                  # YT Industries fait surtout enduro/DH
    "propain": "enduro",             # Propain (Tyee, Spindrift, Rage)
    "transition": "enduro",
    "evil": "enduro",
    "intense": "enduro",
    "polygon": "enduro",
    "guerrilla": "enduro",
    "pivot": "enduro",
    "wereldlijst": "enduro",
}


# Mapping precis (marque, modele) -> categorie. Cle = (brand_normalized, model_prefix_normalized).
MODEL_MAPPING: dict[tuple[str, str], VttCategory] = {
    # --- Specialized ---
    ("specialized", "epic"): "xc",
    ("specialized", "chisel"): "xc",
    ("specialized", "fuse"): "trail",          # hardtail trail
    ("specialized", "stumpjumper"): "all_mountain",  # 140-150mm en general
    ("specialized", "stumpjumperevo"): "enduro",     # version EVO 160mm
    ("specialized", "enduro"): "enduro",
    ("specialized", "demo"): "dh",
    ("specialized", "kenevo"): "enduro",       # VAE enduro
    ("specialized", "levo"): "all_mountain",   # VAE trail/AM
    ("specialized", "turbolevo"): "all_mountain",
    ("specialized", "p"): "dirt",              # P.1, P.2, P.3 dirt jump
    ("specialized", "p1"): "dirt",
    ("specialized", "p2"): "dirt",
    ("specialized", "p3"): "dirt",

    # --- Trek ---
    ("trek", "supercaliber"): "xc",
    ("trek", "topfuel"): "xc",
    ("trek", "fuelex"): "trail",
    ("trek", "fuelexe"): "trail",              # VAE trail
    ("trek", "rail"): "all_mountain",          # VAE AM
    ("trek", "remedy"): "all_mountain",
    ("trek", "slash"): "enduro",
    ("trek", "session"): "dh",
    ("trek", "ticket"): "dirt",

    # --- Santa Cruz ---
    ("santacruz", "blur"): "xc",
    ("santacruz", "highball"): "xc",
    ("santacruz", "tallboy"): "trail",
    ("santacruz", "5010"): "trail",
    ("santacruz", "hightower"): "all_mountain",
    ("santacruz", "bronson"): "all_mountain",
    ("santacruz", "bullit"): "enduro",         # VAE enduro
    ("santacruz", "megatower"): "enduro",
    ("santacruz", "nomad"): "enduro",
    ("santacruz", "v10"): "dh",
    ("santacruz", "vala"): "trail",            # VAE trail recent
    ("santacruz", "heckler"): "all_mountain",  # VAE AM

    # --- Commencal ---
    ("commencal", "meta"): "all_mountain",     # Meta TR/AM/HT 140-150mm
    ("commencal", "metaht"): "all_mountain",
    ("commencal", "metatr"): "all_mountain",
    ("commencal", "metaam"): "enduro",         # AM = 160mm chez Commencal moderne
    ("commencal", "metasx"): "enduro",
    ("commencal", "metapower"): "enduro",      # VAE enduro
    ("commencal", "clash"): "enduro",
    ("commencal", "supreme"): "dh",
    ("commencal", "furious"): "dh",
    ("commencal", "absolut"): "dirt",

    # --- Lapierre ---
    ("lapierre", "xrm"): "xc",
    ("lapierre", "prorace"): "xc",
    ("lapierre", "zesty"): "all_mountain",
    ("lapierre", "spicy"): "enduro",
    ("lapierre", "overvolt"): "all_mountain",  # VAE trail/AM
    ("lapierre", "ezesty"): "all_mountain",
    ("lapierre", "dh"): "dh",
    ("lapierre", "gravitydh"): "dh",

    # --- Cube ---
    ("cube", "reaction"): "xc",
    ("cube", "ams"): "xc",                     # AMS 100/120 = XC/trail
    ("cube", "stereo"): "all_mountain",        # Stereo 140-150
    ("cube", "stereohpa"): "all_mountain",
    ("cube", "stereoone"): "enduro",           # Stereo One = 160-170
    ("cube", "two15"): "enduro",
    ("cube", "hanzz"): "enduro",
    ("cube", "tworace"): "dh",

    # --- Canyon ---
    ("canyon", "lux"): "xc",
    ("canyon", "neuron"): "trail",
    ("canyon", "spectral"): "all_mountain",
    ("canyon", "torque"): "enduro",
    ("canyon", "strive"): "enduro",
    ("canyon", "sender"): "dh",
    ("canyon", "stitched"): "dirt",

    # --- Nukeproof ---
    ("nukeproof", "scout"): "trail",
    ("nukeproof", "reactor"): "all_mountain",
    ("nukeproof", "mega"): "enduro",
    ("nukeproof", "giga"): "enduro",
    ("nukeproof", "dissent"): "dh",

    # --- YT (defaut enduro mais specifie) ---
    ("yt", "izzo"): "trail",
    ("yt", "jeffsy"): "all_mountain",
    ("yt", "capra"): "enduro",
    ("yt", "tues"): "dh",

    # --- Giant ---
    ("giant", "anthem"): "xc",
    ("giant", "stance"): "trail",
    ("giant", "trance"): "all_mountain",
    ("giant", "reign"): "enduro",
    ("giant", "glory"): "dh",

    # --- Scott ---
    ("scott", "spark"): "xc",
    ("scott", "genius"): "all_mountain",
    ("scott", "ransom"): "enduro",
    ("scott", "voltage"): "dh",
    ("scott", "gambler"): "dh",

    # --- Norco ---
    ("norco", "revolver"): "xc",
    ("norco", "fluid"): "trail",
    ("norco", "optic"): "trail",
    ("norco", "sight"): "all_mountain",
    ("norco", "range"): "enduro",
    ("norco", "shore"): "enduro",
    ("norco", "aurum"): "dh",

    # --- Orbea ---
    ("orbea", "alma"): "xc",
    ("orbea", "oiz"): "xc",
    ("orbea", "occam"): "all_mountain",
    ("orbea", "rallon"): "enduro",
    ("orbea", "rise"): "all_mountain",         # VAE AM

    # --- Mondraker ---
    ("mondraker", "podium"): "xc",
    ("mondraker", "chrono"): "xc",
    ("mondraker", "raze"): "trail",
    ("mondraker", "foxy"): "all_mountain",
    ("mondraker", "superfoxy"): "enduro",
    ("mondraker", "dune"): "enduro",
    ("mondraker", "summum"): "dh",

    # --- Kona ---
    ("kona", "honzo"): "trail",                # hardtail trail
    ("kona", "process"): "all_mountain",
    ("kona", "operator"): "dh",
    ("kona", "shonky"): "dirt",

    # --- BMC ---
    ("bmc", "fourstroke"): "xc",
    ("bmc", "agonist"): "xc",
    ("bmc", "speedfox"): "trail",
    ("bmc", "trailfox"): "all_mountain",

    # --- Rocky Mountain ---
    ("rockymountain", "element"): "xc",
    ("rockymountain", "growler"): "trail",
    ("rockymountain", "instinct"): "all_mountain",
    ("rockymountain", "altitude"): "all_mountain",
    ("rockymountain", "slayer"): "enduro",
    ("rockymountain", "maiden"): "dh",

    # --- Vitus ---
    ("vitus", "rapide"): "xc",
    ("vitus", "mythique"): "trail",
    ("vitus", "escarpe"): "all_mountain",
    ("vitus", "sommet"): "enduro",

    # --- Whyte ---
    ("whyte", "905"): "trail",
    ("whyte", "g160"): "enduro",
    ("whyte", "g170"): "enduro",
    ("whyte", "t160"): "enduro",

    # --- Decathlon (BTWIN / Rockrider) ---
    ("btwin", "rockrider"): "trail",
    ("btwin", "rockraider"): "trail",
    ("rockrider", "st"): "trail",              # ST120, ST520
    ("rockrider", "exp"): "trail",
    ("rockrider", "race"): "xc",
    ("rockrider", "all"): "all_mountain",      # ALL MOUNTAIN
    ("rockrider", "am"): "all_mountain",
    ("rockrider", "e"): "trail",               # E-ST, E-Expl

    # --- Marques DH/freeride pures ---
    ("intense", "m"): "dh",                    # M16, M9, M279
    ("intense", "tracer"): "enduro",
    ("intense", "primer"): "all_mountain",

    # --- Polygon (auto enduro) ---
    ("polygon", "siskiu"): "all_mountain",
    ("polygon", "xtrada"): "trail",
}


def classify_by_model(brand: Optional[str], model: Optional[str]) -> Optional[VttCategory]:
    """Tente de classifier un VTT par mapping (marque, modele).
    Retourne None si rien ne matche (a priori l'enricher fera le fallback IA)."""
    if not brand or not model:
        return None
    b = _norm(brand)
    m = _norm(model)
    if not b or not m:
        return None

    # Test : on cherche si un prefixe du modele matche dans le mapping pour cette marque.
    # On essaie les cles du plus long au plus court pour preferer la specialisation.
    candidates = sorted(
        ((mb, mm) for (mb, mm) in MODEL_MAPPING if mb == b),
        key=lambda x: -len(x[1]),
    )
    for (mb, mm) in candidates:
        if m.startswith(mm):
            return MODEL_MAPPING[(mb, mm)]

    # Fallback : marque entiere a une categorie par defaut connue ?
    if b in BRAND_DEFAULTS:
        return BRAND_DEFAULTS[b]

    return None
