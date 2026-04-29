// Gestion du theme light/dark/auto. Persiste dans localStorage et applique
// data-theme="light"|"dark" sur <html>. "auto" = suit prefers-color-scheme.
import { ref, watch } from "vue";

export type ThemeMode = "light" | "dark" | "auto";

const STORAGE_KEY = "ttv-theme";

function readStored(): ThemeMode {
  if (typeof localStorage === "undefined") return "auto";
  const v = localStorage.getItem(STORAGE_KEY);
  if (v === "light" || v === "dark" || v === "auto") return v;
  return "auto";
}

function systemPrefersDark(): boolean {
  if (typeof window === "undefined" || !window.matchMedia) return false;
  return window.matchMedia("(prefers-color-scheme: dark)").matches;
}

function applyTheme(mode: ThemeMode) {
  if (typeof document === "undefined") return;
  const html = document.documentElement;
  const effective = mode === "auto" ? (systemPrefersDark() ? "dark" : "light") : mode;
  html.setAttribute("data-theme", effective);
}

const theme = ref<ThemeMode>(readStored());

// Applique au boot.
applyTheme(theme.value);

// Re-applique a chaque changement.
watch(theme, (m) => {
  applyTheme(m);
  if (typeof localStorage !== "undefined") localStorage.setItem(STORAGE_KEY, m);
});

// Si "auto", ecouter les changements OS.
if (typeof window !== "undefined" && window.matchMedia) {
  const mq = window.matchMedia("(prefers-color-scheme: dark)");
  mq.addEventListener("change", () => {
    if (theme.value === "auto") applyTheme("auto");
  });
}

export function useTheme() {
  return { theme };
}
