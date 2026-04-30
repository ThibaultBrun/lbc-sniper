// Gestion du consentement RGPD pour le tracking et les pubs.
//
// Approche : Google Consent Mode v2.
//   - Les scripts AdSense + (futur) GA sont charges depuis index.html avec
//     ad_storage / analytics_storage = 'denied' par defaut.
//   - Si l'utilisateur accepte, on met a jour les flags via gtag('consent', 'update', ...).
//   - Si refuse, on ne fait rien (les flags restent denied -> pas de cookie depose).
//
// Stockage du choix : localStorage `ttv-cookies-consent` (JSON, expiration 13 mois CNIL).

import { ref } from "vue";

export type ConsentStatus = "accepted" | "rejected" | "unknown";

const STORAGE_KEY = "ttv-cookies-consent";
const TTL_DAYS = 395; // ~13 mois CNIL

// ID GA4 (Trouve Ton VTT). Le tag se charge UNIQUEMENT si l'utilisateur
// accepte les cookies (RGPD : Consent Mode v2 init dans index.html avec
// analytics_storage=denied par defaut, update vers granted via accept()).
const GA_MEASUREMENT_ID = "G-FNC1SBPZQJ";

interface StoredConsent {
  v: 1;
  status: "accepted" | "rejected";
  at: string;
}

declare global {
  interface Window {
    dataLayer?: unknown[];
    gtag?: (...args: unknown[]) => void;
  }
}

function readStored(): StoredConsent | null {
  if (typeof localStorage === "undefined") return null;
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as StoredConsent;
    if (!parsed || parsed.v !== 1) return null;
    const ageMs = Date.now() - new Date(parsed.at).getTime();
    if (ageMs > TTL_DAYS * 24 * 3600 * 1000) {
      localStorage.removeItem(STORAGE_KEY);
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

function writeStored(status: "accepted" | "rejected") {
  const data: StoredConsent = {
    v: 1,
    status,
    at: new Date().toISOString(),
  };
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
}

const consent = ref<ConsentStatus>(readStored()?.status ?? "unknown");

function updateGtagConsent(granted: boolean) {
  if (typeof window === "undefined" || !window.gtag) return;
  const value = granted ? "granted" : "denied";
  window.gtag("consent", "update", {
    ad_storage: value,
    ad_user_data: value,
    ad_personalization: value,
    analytics_storage: value,
  });
}

function loadGAIfNeeded() {
  if (!GA_MEASUREMENT_ID) return;
  if (typeof document === "undefined") return;
  if (document.querySelector(`script[src*="googletagmanager.com/gtag/js?id=${GA_MEASUREMENT_ID}"]`)) return;

  const loader = document.createElement("script");
  loader.async = true;
  loader.src = `https://www.googletagmanager.com/gtag/js?id=${GA_MEASUREMENT_ID}`;
  document.head.appendChild(loader);

  if (window.gtag) {
    window.gtag("js", new Date());
    // send_page_view: false -> on envoie nous-meme les page_view au changement
    // de route SPA via trackPageView(), sinon GA ne voit que la 1ere page.
    window.gtag("config", GA_MEASUREMENT_ID, {
      anonymize_ip: true,
      send_page_view: false,
    });
    // Premier hit : la page d'arrivee.
    trackPageView(window.location.pathname + window.location.search);
  }
}

// Envoie un page_view a GA. A appeler depuis le router Vue.
// Si GA n'est pas charge (consent denied / config vide), no-op silencieux.
export function trackPageView(path: string, title?: string) {
  if (typeof window === "undefined" || !window.gtag || !GA_MEASUREMENT_ID) return;
  if (consent.value !== "accepted") return;
  window.gtag("event", "page_view", {
    page_path: path,
    page_title: title ?? document.title,
    page_location: window.location.href,
  });
}

export function useConsent() {
  function accept() {
    writeStored("accepted");
    consent.value = "accepted";
    updateGtagConsent(true);
    loadGAIfNeeded();
  }

  function reject() {
    writeStored("rejected");
    consent.value = "rejected";
    updateGtagConsent(false);
  }

  function reopen() {
    if (typeof localStorage !== "undefined") localStorage.removeItem(STORAGE_KEY);
    consent.value = "unknown";
  }

  return { consent, accept, reject, reopen };
}

// Au boot : si l'utilisateur a deja un choix stocke, on l'applique tout de suite.
if (typeof window !== "undefined") {
  if (consent.value === "accepted") {
    updateGtagConsent(true);
    loadGAIfNeeded();
  } else if (consent.value === "rejected") {
    updateGtagConsent(false);
  }
  // "unknown" : on ne touche pas, le default 'denied' de index.html reste.
}
