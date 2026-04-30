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

function loadProfileInBackground(uid: string) {
  // Charge le profile sans bloquer le caller. Met a jour `profile.value`
  // quand la donnee arrive (la reactivite Vue propage aux composants qui
  // dependent de isAdmin / profile.avatar_url).
  // Dedup : si on a deja chargE pour ce uid OU si une requete est en vol,
  // on ne relance rien.
  if (profileLoadedFor === uid && profile.value) return;
  if (profileInflight) return;
  profileLoadedFor = uid;

  // Timeout court : au-dela, on abandonne. On ne bloque plus l'app.
  const TIMEOUT_MS = 3000;
  const timeoutPromise = new Promise<null>((resolve) => {
    setTimeout(() => resolve(null), TIMEOUT_MS);
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
  profileInflight
    .then((p) => {
      if (p) profile.value = p;
    })
    .catch((e) => console.error("Profile load failed", e))
    .finally(() => {
      profileInflight = null;
    });
}

function setUserAndProfile(newUser: User | null) {
  // PAS async : on ne bloque plus le caller (syncFromSession / onAuthStateChange).
  // Le profile se charge en background, l'app peut continuer avec juste user.
  const newUid = newUser?.id ?? null;
  user.value = newUser;
  if (!newUid) {
    profile.value = null;
    profileLoadedFor = null;
    profileInflight = null;
    return;
  }
  if (profileLoadedFor === newUid && profile.value) return;
  loadProfileInBackground(newUid);
}

async function syncFromSession() {
  const { data } = await supabase.auth.getSession();
  setUserAndProfile(data.session?.user ?? null);
  loading.value = false;
}

function ensureInit() {
  if (initialized) return;
  initialized = true;
  syncFromSession();
  // Tient l'etat a jour si l'utilisateur se logge / log out dans un autre onglet.
  // Note : Supabase declenche un evenement INITIAL_SESSION au boot meme si on
  // a deja appele getSession(). Notre dedup via profileLoadedFor evite de
  // re-fetch dans ce cas.
  supabase.auth.onAuthStateChange((_event, session) => {
    setUserAndProfile(session?.user ?? null);
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
