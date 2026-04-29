import { onMounted, ref, computed } from "vue";
import type { User } from "@supabase/supabase-js";
import { supabase } from "./supabase";

export type Profile = {
  id: string;
  email: string | null;
  display_name: string | null;
  avatar_url: string | null;
  role: "user" | "admin";
  created_at: string;
  updated_at: string;
};

// Etat global partage entre tous les composants qui utilisent useAuth().
// Pas reactive cross-tab (Supabase JS gere ca via onAuthStateChange + localStorage).
const user = ref<User | null>(null);
const profile = ref<Profile | null>(null);
const loading = ref(true);

let initialized = false;

async function loadProfile(uid: string) {
  const { data, error } = await supabase
    .from("profiles")
    .select("*")
    .eq("id", uid)
    .maybeSingle();
  if (error) {
    console.error("Failed to load profile", error);
    return null;
  }
  return data as Profile | null;
}

async function syncFromSession() {
  const { data } = await supabase.auth.getSession();
  user.value = data.session?.user ?? null;
  profile.value = user.value ? await loadProfile(user.value.id) : null;
  loading.value = false;
}

function ensureInit() {
  if (initialized) return;
  initialized = true;
  syncFromSession();
  // Tient l'etat a jour si l'utilisateur se logge / log out dans un autre onglet.
  supabase.auth.onAuthStateChange(async (_event, session) => {
    user.value = session?.user ?? null;
    profile.value = user.value ? await loadProfile(user.value.id) : null;
  });
}

export function useAuth() {
  ensureInit();
  // En cas de remount on s'assure d'avoir des donnees fraiches sans bloquer
  onMounted(() => {
    if (!loading.value) return;
  });

  const isAuthenticated = computed(() => user.value !== null);
  const isAdmin = computed(() => profile.value?.role === "admin");

  async function signInWithGoogle() {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}${window.location.pathname}`,
      },
    });
    if (error) {
      console.error("OAuth signin failed", error);
      throw error;
    }
  }

  async function signOut() {
    await supabase.auth.signOut();
    user.value = null;
    profile.value = null;
  }

  return { user, profile, loading, isAuthenticated, isAdmin, signInWithGoogle, signOut };
}
