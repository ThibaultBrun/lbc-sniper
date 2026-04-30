import { ref, watch } from "vue";
import { useAuth } from "./auth";
import { supabase } from "./supabase";
import type { GeoFilterValue } from "./components/GeoFilter.vue";

// Snapshot de tous les filtres UI courants. Stocke en jsonb.
export type SavedSearchFilters = {
  categoryFilter: string | null;
  vttCategoryFilter?: string | null;   // xc | all_mountain | enduro | dh | dirt
  sizeFilter?: string | null;          // XS | S | M | L | XL | XXL
  wheelFilter?: string | null;         // 20 | 24 | 26 | 27.5 | 29
  geo: GeoFilterValue | null;
  radiusKm: number;
  electricFilter: "all" | "yes" | "no";
  priceMin: number | null;
  priceMax: number | null;
  searchText: string;
  sortBy: "deal" | "price" | "recent";
  minDealScore?: number; // utile pour les alertes mail
};

export type SavedSearch = {
  id: string;
  user_id: string;
  name: string;
  filters: SavedSearchFilters;
  notify_mode: "off" | "instant" | "daily";
  last_notified_at: string | null;
  created_at: string;
  updated_at: string;
};

const searches = ref<SavedSearch[]>([]);
const loaded = ref(false);

let initialized = false;
let loadedForUserId: string | null = null;
let loadInflight: Promise<void> | null = null;

async function load(userId: string) {
  if (loadedForUserId === userId) return;
  if (loadInflight) return loadInflight;
  loadInflight = (async () => {
    const { data, error } = await supabase
      .from("saved_searches")
      .select("*")
      .eq("user_id", userId)
      .order("created_at", { ascending: false });
    if (error) {
      console.error("Failed to load saved searches", error);
      return;
    }
    searches.value = (data ?? []) as SavedSearch[];
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
        searches.value = [];
        loaded.value = false;
        loadedForUserId = null;
      }
    },
    { immediate: true },
  );
}

export function useSavedSearches() {
  ensureInit();
  const { user, isAuthenticated } = useAuth();

  async function save(name: string, filters: SavedSearchFilters, notify_mode: "off" | "instant" | "daily" = "daily") {
    if (!user.value) throw new Error("Sign in required");
    const { data, error } = await supabase
      .from("saved_searches")
      .insert({
        user_id: user.value.id,
        name,
        filters,
        notify_mode,
      })
      .select()
      .single();
    if (error) {
      console.error("Failed to save search", error);
      throw error;
    }
    searches.value = [data as SavedSearch, ...searches.value];
    return data as SavedSearch;
  }

  async function update(id: string, patch: Partial<Pick<SavedSearch, "name" | "filters" | "notify_mode">>) {
    if (!user.value) throw new Error("Sign in required");
    const { data, error } = await supabase
      .from("saved_searches")
      .update(patch)
      .eq("id", id)
      .eq("user_id", user.value.id)
      .select()
      .single();
    if (error) {
      console.error("Failed to update search", error);
      throw error;
    }
    const idx = searches.value.findIndex((s) => s.id === id);
    if (idx >= 0) searches.value[idx] = data as SavedSearch;
  }

  async function remove(id: string) {
    if (!user.value) throw new Error("Sign in required");
    const { error } = await supabase
      .from("saved_searches")
      .delete()
      .eq("id", id)
      .eq("user_id", user.value.id);
    if (error) {
      console.error("Failed to delete search", error);
      throw error;
    }
    searches.value = searches.value.filter((s) => s.id !== id);
  }

  return {
    searches,
    loaded,
    isAuthenticated,
    save,
    update,
    remove,
  };
}
