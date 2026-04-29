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
// Dedup : on memorise le dernier user.id pour lequel le profile a ete charge.
// Sans ca, getSession() + onAuthStateChange (immediat puis SIGNED_IN) declenchent
// 2-3 chargements concurrents du meme profile.
let profileLoadedFor: string | null = null;
let profileInflight: Promise<Profile | null> | null = null;

async function loadProfile(uid: string): Promise<Profile | null> {
  // Dedup : si on a deja le profile pour ce user, on retourne le cache.
  if (profileLoadedFor === uid && profile.value) return profile.value;
  // Si une requete est en vol pour le meme user, on l'attend plutot que d'en lancer une autre.
  if (profileInflight) return profileInflight;

  const TIMEOUT_MS = 8000;
  const timeoutPromise = new Promise<null>((resolve) => {
    setTimeout(() => {
      console.warn("loadProfile timeout — continuing without profile");
      resolve(null);
    }, TIMEOUT_MS);
  });
  const queryPromise = supabase
    .from("profiles")
    .select("*")
    .eq("id", uid)
    .maybeSingle()
    .then(({ data, error }) => {
      if (error) {
        console.error("Failed to load profile", error);
        return null;
      }
      return data as Profile | null;
    });
  profileInflight = Promise.race([queryPromise, timeoutPromise]);
  try {
    const p = await profileInflight;
    if (p) profileLoadedFor = uid;
    return p;
  } finally {
    profileInflight = null;
  }
}

async function setUserAndProfile(newUser: User | null) {
  // Si l'user.id est le meme qu'avant, on ne re-fetch pas le profile.
  const prevUid = user.value?.id ?? null;
  const newUid = newUser?.id ?? null;
  user.value = newUser;
  if (!newUser) {
    profile.value = null;
    profileLoadedFor = null;
    return;
  }
  if (prevUid === newUid && profileLoadedFor === newUid) return;
  profile.value = await loadProfile(newUser.id);
}

async function syncFromSession() {
  const { data } = await supabase.auth.getSession();
  await setUserAndProfile(data.session?.user ?? null);
  loading.value = false;
}

function ensureInit() {
  if (initialized) return;
  initialized = true;
  syncFromSession();
  // Tient l'etat a jour si l'utilisateur se logge / log out dans un autre onglet.
  supabase.auth.onAuthStateChange(async (_event, session) => {
    await setUserAndProfile(session?.user ?? null);
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
    // On reset le state local AVANT l'appel reseau pour que l'UI reagisse
    // immediatement, meme si l'appel Supabase est lent ou plante.
    user.value = null;
    profile.value = null;
    try {
      await supabase.auth.signOut();
    } catch (e) {
      console.error("signOut failed (state already reset locally)", e);
    }
  }

  return { user, profile, loading, isAuthenticated, isAdmin, signInWithGoogle, signOut };
}
