"""Envoie un mail de test pour valider la config SMTP OVH.

Usage : python -m scraper.test_mail t.brun@geomatika.fr
"""

import sys

from .notifier import close_smtp, send_mail


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python -m scraper.test_mail <destinataire@example.com>")
        return 1
    to = sys.argv[1]
    html = """<html><body>
      <h1 style="color:#10b981">Ca marche !</h1>
      <p>Mail de test envoye depuis le SMTP OVH (bonjour@trouvetonvtt.fr).</p>
      <p>Si tu vois ce mail, le notifier va pouvoir envoyer les alertes.</p>
    </body></html>"""
    print(f"Sending test mail to {to}...")
    ok = send_mail(to, "[Trouve Ton VTT] Test SMTP OVH", html)
    close_smtp()
    print("OK" if ok else "FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
