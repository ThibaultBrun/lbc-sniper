import { supabase } from "./supabase";

const NOTIFY_ENABLED_KEY = "ttv_notify_enabled";
const LAST_SEEN_ID_KEY = "ttv_notify_last_seen_id";
const POLL_MS = 90_000;

let pollTimer: ReturnType<typeof setInterval> | null = null;

function canNotify(): boolean {
  return typeof window !== "undefined" && "Notification" in window;
}

export function isNotificationEnabled(): boolean {
  if (!canNotify()) return false;
  return localStorage.getItem(NOTIFY_ENABLED_KEY) === "1";
}

export async function enableNotifications(): Promise<boolean> {
  if (!canNotify()) return false;
  const permission = await Notification.requestPermission();
  const granted = permission === "granted";
  localStorage.setItem(NOTIFY_ENABLED_KEY, granted ? "1" : "0");
  return granted;
}

async function notify(title: string, body: string, href: string) {
  if (!canNotify() || Notification.permission !== "granted") return;

  if ("serviceWorker" in navigator) {
    const reg = await navigator.serviceWorker.ready;
    await reg.showNotification(title, {
      body,
      icon: "/favicon.svg",
      badge: "/favicon.svg",
      data: { href },
    });
    return;
  }

  const n = new Notification(title, { body, icon: "/favicon.svg" });
  n.onclick = () => {
    window.open(href, "_blank");
  };
}

async function checkNewGreatDeals() {
  const { data, error } = await supabase
    .from("listings")
    .select("id,subject,city,current_price,deal_score,first_seen_at")
    .eq("is_active", true)
    .eq("admin_hidden", false)
    .gte("deal_score", 80)
    .order("id", { ascending: false })
    .limit(1);

  if (error || !data || data.length === 0) return;

  const latest = data[0];
  const lastSeenId = Number(localStorage.getItem(LAST_SEEN_ID_KEY) ?? "0");

  if (!Number.isFinite(lastSeenId) || lastSeenId <= 0) {
    localStorage.setItem(LAST_SEEN_ID_KEY, String(latest.id));
    return;
  }

  if (latest.id <= lastSeenId) return;

  localStorage.setItem(LAST_SEEN_ID_KEY, String(latest.id));
  const price = latest.current_price ? `${latest.current_price} EUR` : "prix NC";
  const city = latest.city || "ville inconnue";
  await notify("Nouvelle excellente affaire VTT", `${latest.subject} - ${price} - ${city}`, `/ad/${latest.id}`);
}

export async function startNotificationsPolling() {
  if (!isNotificationEnabled() || Notification.permission !== "granted") return;
  await checkNewGreatDeals();
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = setInterval(() => {
    void checkNewGreatDeals();
  }, POLL_MS);
}

export function stopNotificationsPolling() {
  if (pollTimer) clearInterval(pollTimer);
  pollTimer = null;
}
