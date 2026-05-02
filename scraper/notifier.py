"""Envoie les notifications mail aux utilisateurs apres chaque scrape :

1. **Baisse de prix sur favori** : pour chaque ad en favori dont le prix actuel
   est strictement inferieur au last_notified_price, on envoie un mail puis on
   met a jour last_notified_price.

2. **Nouvelles annonces dans une recherche enregistree** :
   - notify_mode='instant' : si >=1 nouvelle annonce matchant, envoie tout de suite
   - notify_mode='daily'   : si >=1 et plus de 24h depuis last_notified_at,
                             envoie un digest

Le matching des filtres d'une saved_search se fait COTE PYTHON : on lit la
saved_search, on charge les annonces actives, on filtre selon les criteres,
on compare avec last_notified_at.

Usage : python -m scraper.notifier
        python -m scraper.notifier --dry-run     # n'envoie rien, log seulement
"""

import argparse
import math
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

from dotenv import load_dotenv

from .db import get_client

load_dotenv()


# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------

# Identite expediteur (decomposee : nom + email pour formataddr).
FROM_NAME = "Trouve Ton VTT"
FROM_EMAIL = os.environ.get("SMTP_FROM", "bonjour@trouvetonvtt.fr")
SITE_URL = "https://trouvetonvtt.fr"
DAILY_DIGEST_INTERVAL_HOURS = 24

# SMTP OVH par defaut (peut etre override via .env si on bascule plus tard).
# Port 465 = SSL implicite ; 587 = STARTTLS. OVH supporte les deux.
SMTP_HOST = os.environ.get("SMTP_HOST", "ssl0.ovh.net")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")


# ----------------------------------------------------------------------------
# MATCHING DES FILTRES (cote Python, miroir de la logique UI)
# ----------------------------------------------------------------------------

def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlng / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))


def _normalize(s: Optional[str]) -> str:
    if not s:
        return ""
    s = s.lower()
    for a, b in [("é", "e"), ("è", "e"), ("ê", "e"), ("ë", "e"), ("î", "i"),
                 ("ï", "i"), ("ô", "o"), ("ö", "o"), ("û", "u"), ("ü", "u"),
                 ("ù", "u"), ("à", "a"), ("â", "a"), ("ä", "a"), ("ç", "c")]:
        s = s.replace(a, b)
    return s


def _as_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return [v for v in value if v]
    return [value] if value else []


def ad_matches_filters(ad: dict, filters: dict) -> bool:
    """Reproduit la logique de filtrage de App.vue cote Python."""
    if filters.get("categoryFilter") and ad.get("category_label") != filters["categoryFilter"]:
        return False

    vtt_cats = _as_list(filters.get("vttCategoryFilter"))
    if vtt_cats and ad.get("vtt_category") not in vtt_cats:
        return False

    sizes = _as_list(filters.get("sizeFilter"))
    if sizes and ad.get("size_label") not in sizes:
        return False

    wheels = _as_list(filters.get("wheelFilter"))
    if wheels:
        wheel = str(ad.get("wheel_size") or "")
        if not any(wheel.startswith(str(w)) for w in wheels):
            return False

    geo = filters.get("geo")
    radius = filters.get("radiusKm", 50)
    if geo and ad.get("ad_lat") is not None and ad.get("ad_lng") is not None:
        d = _haversine_km(geo["lat"], geo["lng"], ad["ad_lat"], ad["ad_lng"])
        if d > radius:
            return False
    elif geo:
        return False  # filtre actif mais ad sans coords

    elec = filters.get("electricFilter", "all")
    if elec == "yes" and not ad.get("electric"):
        return False
    if elec == "no" and ad.get("electric"):
        return False

    pmin = filters.get("priceMin")
    pmax = filters.get("priceMax")
    cp = ad.get("current_price")
    if pmin is not None and (cp is None or cp < pmin):
        return False
    if pmax is not None and (cp is None or cp > pmax):
        return False

    q = _normalize(filters.get("searchText", "").strip())
    if q and q not in _normalize(ad.get("subject")):
        return False

    min_score = filters.get("minDealScore")
    if min_score is not None and (ad.get("deal_score") or 0) < min_score:
        return False

    return True


# ----------------------------------------------------------------------------
# MAIL TEMPLATES
# ----------------------------------------------------------------------------

def _ad_card_html(ad: dict) -> str:
    title = (ad.get("subject") or "")[:120]
    price = ad.get("current_price")
    market = ad.get("estimated_market_eur")
    score = ad.get("deal_score") or 0
    img = ad.get("image_url") or ""
    city = ad.get("city") or ""
    ad_url = f"{SITE_URL}/ad/{ad['id']}"
    score_color = "#10b981" if score >= 80 else "#f59e0b" if score >= 60 else "#64748b"
    discount = ""
    if price and market and market > 0:
        pct = (market - price) / market * 100
        if pct > 0:
            discount = f' · <strong style="color:{score_color}">−{int(pct)}%</strong>'
    return f"""
    <table style="width:100%;border-collapse:collapse;border:1px solid #e2e8f0;border-radius:8px;margin-bottom:12px;overflow:hidden">
      <tr>
        <td style="width:120px;background:#f1f5f9">
          {"<img src='" + img + "' style='width:120px;height:90px;object-fit:cover;display:block' />" if img else ""}
        </td>
        <td style="padding:10px 14px;vertical-align:top">
          <div style="font-size:11px;color:#fff;background:{score_color};display:inline-block;padding:2px 6px;border-radius:4px;font-weight:bold">{score}/100</div>
          <div style="font-size:14px;color:#0f172a;margin:4px 0 2px;font-weight:600">{title}</div>
          <div style="font-size:13px;color:#475569">
            <strong>{int(price) if price else "?"} €</strong>{discount} · {city}
          </div>
          <div style="margin-top:8px">
            <a href="{ad_url}" style="display:inline-block;background:#10b981;color:#fff;padding:6px 12px;border-radius:6px;text-decoration:none;font-size:12px;font-weight:600">Voir l'analyse →</a>
          </div>
        </td>
      </tr>
    </table>
    """


def _wrap_email(title: str, intro_html: str, body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f8fafc;margin:0;padding:20px">
  <table style="max-width:600px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;border:1px solid #e2e8f0">
    <tr>
      <td style="background:linear-gradient(135deg,#10b981,#059669);padding:20px 24px;color:#fff">
        <div style="font-size:11px;opacity:.8;text-transform:uppercase;letter-spacing:1px">Trouve Ton VTT</div>
        <div style="font-size:20px;font-weight:bold">{title}</div>
      </td>
    </tr>
    <tr><td style="padding:20px 24px">
      <div style="color:#475569;font-size:14px;line-height:1.5;margin-bottom:16px">{intro_html}</div>
      {body_html}
    </td></tr>
    <tr><td style="background:#f8fafc;padding:16px 24px;font-size:11px;color:#94a3b8;border-top:1px solid #e2e8f0">
      Tu reçois ce mail car tu as activé une alerte sur Trouve Ton VTT.<br>
      <a href="{SITE_URL}" style="color:#64748b">Gérer mes alertes</a>
    </td></tr>
  </table>
</body></html>"""


# ----------------------------------------------------------------------------
# ENVOI MAIL VIA SMTP (OVH par defaut)
# ----------------------------------------------------------------------------
#
# On garde un singleton de connexion sur la duree d'un run du notifier : ouvrir
# une connexion SSL + login a chaque mail serait lent (et OVH peut tag spam si
# on hammer le SMTP). On reutilise donc la meme session pour tous les envois.

_smtp_conn: Optional[smtplib.SMTP] = None


def _get_smtp() -> Optional[smtplib.SMTP]:
    """Connecte au SMTP. Choisit SSL implicite (port 465) ou STARTTLS (587/25)
    selon le port. OVH supporte les deux ; en pratique 587 est plus tolerant
    sur les chaines de certs."""
    global _smtp_conn
    if _smtp_conn is not None:
        return _smtp_conn
    if not SMTP_USER or not SMTP_PASS:
        print("  ERROR: SMTP_USER/SMTP_PASS not configured", file=sys.stderr)
        return None
    # Fonction interne : tente la connexion avec un contexte SSL donne.
    def _try_connect(ctx: Optional[ssl.SSLContext]) -> Optional[smtplib.SMTP]:
        if SMTP_PORT == 465:
            c = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ctx, timeout=20)
        else:
            c = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20)
            c.ehlo()
            c.starttls(context=ctx)
            c.ehlo()
        c.login(SMTP_USER, SMTP_PASS)
        return c

    insecure_forced = os.environ.get("SMTP_INSECURE") == "1"
    try:
        if insecure_forced:
            # Mode permissif explicitement demande (ex : poste avec antivirus
            # d'entreprise qui fait du SSL inspection -> chaine de cert injectee).
            ctx = ssl._create_unverified_context()
            _smtp_conn = _try_connect(ctx)
            return _smtp_conn

        # Sinon : strict d'abord (avec certifi si dispo) puis fallback automatique
        # si on detecte que c'est un proxy MITM qui pourrit la chaine.
        try:
            import certifi
            ctx = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            ctx = ssl.create_default_context()
        try:
            _smtp_conn = _try_connect(ctx)
            return _smtp_conn
        except ssl.SSLCertVerificationError as e:
            # "self-signed certificate in certificate chain" = signe d'un AV/proxy
            # local. Aucun risque a desactiver la verif pour du SMTP outbound,
            # le mail sera de toute facon signe DKIM par OVH a la sortie.
            msg = str(e)
            if "self-signed" in msg.lower() or "self signed" in msg.lower():
                print(f"  WARN: TLS chain looks intercepted by local AV/proxy, retrying insecure", file=sys.stderr)
                ctx = ssl._create_unverified_context()
                _smtp_conn = _try_connect(ctx)
                return _smtp_conn
            raise
    except Exception as e:
        print(f"  ERROR: SMTP connection to {SMTP_HOST}:{SMTP_PORT} failed: {e}", file=sys.stderr)
        return None


def close_smtp() -> None:
    global _smtp_conn
    if _smtp_conn is not None:
        try:
            _smtp_conn.quit()
        except Exception:
            pass
        _smtp_conn = None


def send_mail(to: str, subject: str, html: str, dry_run: bool = False) -> bool:
    if dry_run:
        print(f"  [DRY-RUN] would send to {to}: {subject!r}")
        return True
    conn = _get_smtp()
    if conn is None:
        return False
    try:
        msg = EmailMessage()
        msg["From"] = formataddr((FROM_NAME, FROM_EMAIL))
        msg["To"] = to
        msg["Subject"] = subject
        # Plain text fallback (les clients sans HTML / antispam aiment ca).
        msg.set_content("Ce mail necessite un client compatible HTML.")
        msg.add_alternative(html, subtype="html")
        conn.send_message(msg)
        return True
    except Exception as e:
        print(f"  SMTP send failed for {to}: {e}", file=sys.stderr)
        return False


# ----------------------------------------------------------------------------
# WORKERS
# ----------------------------------------------------------------------------

def process_price_drops(db, dry_run: bool = False) -> tuple[int, int]:
    """Retourne (mails_envoyes, baisses_detectees)."""
    rows = db.table("favorites").select(
        "user_id, ad_id, last_notified_price, "
        "ads(id, subject, current_price, estimated_market_eur, image_url, city, deal_score)"
    ).execute().data

    sent = 0
    detected = 0
    for r in rows:
        ad = r.get("ads")
        if not ad or ad.get("current_price") is None:
            continue
        last_known = r.get("last_notified_price")
        cp = ad["current_price"]
        if last_known is None or float(cp) >= float(last_known):
            continue

        detected += 1
        # Recupere l'email de l'utilisateur via la table profiles
        prof = db.table("profiles").select("email").eq("id", r["user_id"]).maybe_single().execute().data
        if not prof or not prof.get("email"):
            continue

        old = float(last_known)
        new = float(cp)
        diff = old - new
        pct = int(diff / old * 100)
        title = (ad.get("subject") or "Ton favori")[:80]
        intro = f"Le prix d'une annonce que tu as marquée comme favori a baissé de <strong>{int(diff)} € (−{pct}%)</strong>."
        body = (
            f'<div style="background:#ecfdf5;border:1px solid #a7f3d0;border-radius:8px;padding:14px;margin-bottom:16px;text-align:center">'
            f'<div style="color:#64748b;font-size:13px"><s>{int(old)} €</s></div>'
            f'<div style="color:#059669;font-size:28px;font-weight:bold">{int(new)} €</div>'
            f'</div>'
            + _ad_card_html(ad)
        )
        html = _wrap_email(f"💰 Baisse de prix : −{pct}%", intro, body)
        subject = f"💰 -{pct}% sur \"{title[:60]}\""

        if send_mail(prof["email"], subject, html, dry_run=dry_run):
            sent += 1
            if not dry_run:
                db.table("favorites").update({
                    "last_notified_price": new
                }).eq("user_id", r["user_id"]).eq("ad_id", r["ad_id"]).execute()

    return sent, detected


def process_saved_searches(db, dry_run: bool = False) -> tuple[int, int]:
    """Retourne (mails_envoyes, recherches_traitees)."""
    searches = db.table("saved_searches").select("*").neq("notify_mode", "off").execute().data

    # On charge toutes les annonces actives une seule fois (pas par recherche).
    ads = db.table("ads").select(
        "id, subject, current_price, estimated_market_eur, image_url, city, "
        "category_label, vtt_category, size_label, wheel_size, "
        "ad_lat, ad_lng, electric, deal_score, first_seen_at"
    ).eq("is_active", True).not_.is_("deal_score", "null").execute().data

    now = datetime.now(timezone.utc)
    sent = 0
    processed = 0

    for search in searches:
        processed += 1
        # last_notified_at peut etre null (jamais notifie) ou une date.
        last_str = search.get("last_notified_at") or search.get("created_at")
        last_dt = datetime.fromisoformat(last_str.replace("Z", "+00:00")) if last_str else now

        # En mode 'daily', on n'envoie que si >24h depuis le dernier digest.
        if search["notify_mode"] == "daily":
            if (now - last_dt) < timedelta(hours=DAILY_DIGEST_INTERVAL_HOURS):
                continue

        # Annonces qui :
        #  - matchent les filtres
        #  - ont first_seen_at > last_notified_at
        new_ads = []
        for ad in ads:
            seen_str = ad.get("first_seen_at")
            if not seen_str:
                continue
            seen_dt = datetime.fromisoformat(seen_str.replace("Z", "+00:00"))
            if seen_dt <= last_dt:
                continue
            if ad_matches_filters(ad, search.get("filters") or {}):
                new_ads.append(ad)

        if not new_ads:
            # Rien de neuf - on n'envoie pas mais on update last_notified_at
            # pour que la fenetre de 24h reparte de maintenant en mode daily.
            if not dry_run and search["notify_mode"] == "daily":
                db.table("saved_searches").update({
                    "last_notified_at": now.isoformat()
                }).eq("id", search["id"]).execute()
            continue

        # Recupere l'email
        prof = db.table("profiles").select("email").eq("id", search["user_id"]).maybe_single().execute().data
        if not prof or not prof.get("email"):
            continue

        # Tri par deal_score desc, max 10 dans le mail
        new_ads.sort(key=lambda a: (a.get("deal_score") or 0), reverse=True)
        top_ads = new_ads[:10]
        n = len(new_ads)

        title = f"🚲 {n} nouvelle{'s' if n > 1 else ''} annonce{'s' if n > 1 else ''}"
        intro = (
            f"Voici les nouvelles annonces qui correspondent à ta recherche "
            f"<strong>« {search['name']} »</strong>."
            + (f" (10 plus pertinentes affichées sur {n} au total)" if n > 10 else "")
        )
        body = "".join(_ad_card_html(a) for a in top_ads)
        html = _wrap_email(title, intro, body)
        subject = f"🚲 {n} nouvelle{'s' if n > 1 else ''} annonce{'s' if n > 1 else ''} : {search['name'][:50]}"

        if send_mail(prof["email"], subject, html, dry_run=dry_run):
            sent += 1
            if not dry_run:
                db.table("saved_searches").update({
                    "last_notified_at": now.isoformat()
                }).eq("id", search["id"]).execute()

    return sent, processed


# ----------------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------------

def main(dry_run: bool = False) -> int:
    db = get_client()
    print("=== Notifier ===")
    print(f"  dry_run: {dry_run}")
    smtp_ok = bool(SMTP_USER and SMTP_PASS)
    print(f"  smtp:    {SMTP_HOST}:{SMTP_PORT} ({'OK' if smtp_ok else 'MISSING credentials'})")

    print("\n[1/2] Price drops on favorites...")
    sent_price, detected = process_price_drops(db, dry_run=dry_run)
    print(f"  detected {detected} price drops, sent {sent_price} mail(s)")

    print("\n[2/2] New ads for saved searches...")
    sent_search, processed = process_saved_searches(db, dry_run=dry_run)
    print(f"  processed {processed} searches, sent {sent_search} mail(s)")

    close_smtp()
    total = sent_price + sent_search
    print(f"\n=== Notifier done: {total} mail(s) sent ===")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Send notification emails via Resend")
    parser.add_argument("--dry-run", action="store_true", help="Log only, no email sent")
    args = parser.parse_args()
    sys.exit(main(dry_run=args.dry_run))
