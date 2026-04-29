import { computed, ref, watch } from "vue";
import { useAuth } from "./auth";
import { supabase } from "./supabase";

// Etat global : Set des ad_id en favori pour le user courant.
const favoriteIds = ref<Set<number>>(new Set());
const loaded = ref(false);

let initialized = false;
// Dedup : on memorise le dernier userId charge. Si Supabase Auth declenche
// 2-3 ticks reactifs sur le meme user (getSession puis onAuthStateChange
// puis re-trigger), on ne refait pas la requete a chaque fois.
let loadedForUserId: string | null = null;
let loadInflight: Promise<void> | null = null;

async function load(userId: string) {
  if (loadedForUserId === userId) return;
  if (loadInflight) return loadInflight;
  loadInflight = (async () => {
    const { data, error } = await supabase
      .from("favorites")
      .select("ad_id")
      .eq("user_id", userId);
    if (error) {
      console.error("Failed to load favorites", error);
      return;
    }
    favoriteIds.value = new Set((data ?? []).map((r) => r.ad_id));
    loaded.value = true;
    loadedForUserId = userId;
  })();
  try {
    await loadInflight;
  } finally {
    loadInflight = null;
  }
}

function ensureInit() {
  if (initialized) return;
  initialized = true;

  const { user } = useAuth();
  watch(
    () => user.value?.id ?? null,
    async (uid) => {
      if (uid) {
        await load(uid);
      } else {
        favoriteIds.value = new Set();
        loaded.value = false;
        loadedForUserId = null;
      }
    },
    { immediate: true },
  );
}

export function useFavorites() {
  ensureInit();
  const { user, isAuthenticated } = useAuth();

  function isFavorite(adId: number): boolean {
    return favoriteIds.value.has(adId);
  }

  async function toggle(adId: number, currentPrice: number | null) {
    if (!user.value) {
      throw new Error("Sign in required to favorite");
    }
    if (favoriteIds.value.has(adId)) {
      // Remove
      const { error } = await supabase
        .from("favorites")
        .delete()
        .eq("user_id", user.value.id)
        .eq("ad_id", adId);
      if (error) {
        console.error("Failed to remove favorite", error);
        throw error;
      }
      favoriteIds.value.delete(adId);
      // Vue 3.5 : re-trigger reactivity sur le Set
      favoriteIds.value = new Set(favoriteIds.value);
    } else {
      const { error } = await supabase.from("favorites").insert({
        user_id: user.value.id,
        ad_id: adId,
        price_at_fav: currentPrice,
        last_notified_price: currentPrice,
      });
      if (error) {
        console.error("Failed to add favorite", error);
        throw error;
      }
      favoriteIds.value.add(adId);
      favoriteIds.value = new Set(favoriteIds.value);
    }
  }

  const count = computed(() => favoriteIds.value.size);

  return {
    favoriteIds,
    isFavorite,
    toggle,
    count,
    isAuthenticated,
    loaded,
  };
}
