<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getAdById, supabase, type Ad } from "./supabase";
import DealCard from "./components/DealCard.vue";
import DealModal from "./components/DealModal.vue";
import GeoFilter, { type GeoFilterValue } from "./components/GeoFilter.vue";
import { haversineKm } from "./geo";

const route = useRoute();
const router = useRouter();

// Mode "secret" si l'URL commence par /secret. La home publique restreint
// par defaut aux categories VTT (enduro + DH).
const isSecret = computed(() => route.path.startsWith("/secret"));

const VTT_LABELS = ["VTT enduro", "VTT DH"];

const ads = ref<Ad[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const sortBy = ref<"deal" | "price" | "recent">("deal");
const categoryFilter = ref<string | null>(null);

const geo = ref<GeoFilterValue | null>(null);
const radiusKm = ref(50);
const electricFilter = ref<"all" | "yes" | "no">("all");
const priceMin = ref<number | null>(null);
const priceMax = ref<number | null>(null);

const selectedAd = ref<Ad | null>(null);
const selectedAdLoading = ref(false);

async function syncSelectedFromRoute() {
  const id = route.params.id;
  if (!id || Array.isArray(id)) {
    selectedAd.value = null;
    return;
  }
  const adId = Number(id);
  const inList = ads.value.find((a) => a.id === adId);
  if (inList) {
    selectedAd.value = inList;
    return;
  }
  selectedAdLoading.value = true;
  try {
    selectedAd.value = await getAdById(adId);
  } catch (e) {
    console.error("Failed to fetch ad", adId, e);
    selectedAd.value = null;
  } finally {
    selectedAdLoading.value = false;
  }
}

function openAd(ad: Ad) {
  router.push({
    name: isSecret.value ? "secret-ad" : "ad",
    params: { id: ad.id },
  });
}

function closeAd() {
  router.push({ name: isSecret.value ? "secret" : "home" });
}

watch(() => route.params.id, syncSelectedFromRoute);
watch(isSecret, () => {
  // Reset le filtre catégorie quand on bascule de mode (les options changent)
  categoryFilter.value = null;
});

async function load() {
  loading.value = true;
  error.value = null;
  try {
    const { data, error: e } = await supabase
      .from("ads")
      .select("*")
      .eq("is_active", true)
      .order("deal_score", { ascending: false, nullsFirst: false })
      .limit(1000);
    if (e) throw e;
    ads.value = data as Ad[];
  } catch (e: any) {
    error.value = e.message ?? String(e);
  } finally {
    loading.value = false;
  }
  await syncSelectedFromRoute();
}

onMounted(async () => {
  syncSelectedFromRoute();
  await load();
});

// Annonces du scope (VTT only en public, tout en /secret)
const scoped = computed(() =>
  isSecret.value
    ? ads.value
    : ads.value.filter((a) => a.category_label && VTT_LABELS.includes(a.category_label)),
);

const categories = computed(() => {
  const set = new Set(
    scoped.value.map((a) => a.category_label).filter((c): c is string => !!c),
  );
  return Array.from(set).sort();
});

const filtered = computed(() => {
  let list = scoped.value;
  if (categoryFilter.value)
    list = list.filter((a) => a.category_label === categoryFilter.value);

  // Filtre geographique : Haversine si geo est defini
  if (geo.value) {
    const g = geo.value;
    const r = radiusKm.value;
    list = list.filter((a) => {
      if (a.ad_lat == null || a.ad_lng == null) return false;
      return haversineKm(g.lat, g.lng, a.ad_lat, a.ad_lng) <= r;
    });
  }

  // Filtre electrique
  if (electricFilter.value === "yes") {
    list = list.filter((a) => a.electric === true);
  } else if (electricFilter.value === "no") {
    list = list.filter((a) => a.electric === false);
  }

  // Filtre prix min/max
  if (priceMin.value !== null) {
    const min = priceMin.value;
    list = list.filter((a) => a.current_price !== null && a.current_price >= min);
  }
  if (priceMax.value !== null) {
    const max = priceMax.value;
    list = list.filter((a) => a.current_price !== null && a.current_price <= max);
  }

  if (sortBy.value === "deal") {
    list = [...list].sort((a, b) => (b.deal_score ?? -1) - (a.deal_score ?? -1));
  } else if (sortBy.value === "price") {
    list = [...list].sort(
      (a, b) => (a.current_price ?? Infinity) - (b.current_price ?? Infinity),
    );
  } else {
    list = [...list].sort(
      (a, b) =>
        new Date(b.first_seen_at).getTime() - new Date(a.first_seen_at).getTime(),
    );
  }
  return list;
});

const stats = computed(() => {
  const all = scoped.value;
  const enriched = all.filter((a) => a.deal_score !== null);
  const great = enriched.filter((a) => (a.deal_score ?? 0) >= 80);
  return {
    total: all.length,
    enriched: enriched.length,
    great: great.length,
  };
});
</script>

<template>
  <div class="min-h-screen">
    <header class="border-b border-slate-800 bg-slate-900/40 backdrop-blur sticky top-0 z-10">
      <div class="max-w-7xl mx-auto px-6 py-4 flex flex-wrap items-baseline gap-4 justify-between">
        <div>
          <h1 class="text-xl font-bold tracking-tight">
            <span class="text-emerald-400">LBC</span> Deals
            <span v-if="isSecret" class="ml-2 text-xs font-normal text-rose-400 uppercase tracking-wider">[ secret ]</span>
          </h1>
          <p class="text-xs text-slate-400 mt-0.5">
            <span v-if="isSecret">VTT, voitures, motos — analyse IA complète</span>
            <span v-else>les meilleures affaires VTT du Bon Coin, analysées par IA</span>
          </p>
        </div>
        <div class="flex items-center gap-4 text-xs text-slate-400">
          <span>{{ stats.total }} annonces</span>
          <span>{{ stats.enriched }} analysées</span>
          <span class="text-emerald-400 font-semibold">{{ stats.great }} excellentes</span>
          <button
            @click="load"
            class="rounded bg-slate-800 hover:bg-slate-700 px-3 py-1 text-slate-200 transition"
          >
            ↻ Recharger
          </button>
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-6 py-6 space-y-6">
      <!-- Filtres -->
      <div class="flex flex-wrap items-center gap-4 text-sm rounded-xl border border-slate-800 bg-slate-900/40 p-4">
        <GeoFilter
          v-model="geo"
          v-model:radius-km="radiusKm"
        />

        <label v-if="categories.length > 1" class="flex items-center gap-2">
          <span class="text-slate-400">Catégorie:</span>
          <select
            v-model="categoryFilter"
            class="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-100"
          >
            <option :value="null">Toutes</option>
            <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
          </select>
        </label>

        <label class="flex items-center gap-2">
          <span class="text-slate-400">⚡ Électrique:</span>
          <select
            v-model="electricFilter"
            class="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-100"
          >
            <option value="all">Tous</option>
            <option value="yes">Électrique</option>
            <option value="no">Musculaire</option>
          </select>
        </label>

        <label class="flex items-center gap-1.5">
          <span class="text-slate-400">Prix:</span>
          <input
            v-model.number="priceMin"
            type="number"
            min="0"
            placeholder="min"
            class="w-24 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-100 placeholder:text-slate-500 text-right tabular-nums"
          />
          <span class="text-slate-500">–</span>
          <input
            v-model.number="priceMax"
            type="number"
            min="0"
            placeholder="max"
            class="w-24 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-100 placeholder:text-slate-500 text-right tabular-nums"
          />
          <span class="text-slate-500">€</span>
        </label>

        <label class="flex items-center gap-2">
          <span class="text-slate-400">Tri:</span>
          <select
            v-model="sortBy"
            class="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-100"
          >
            <option value="deal">Score IA ↓</option>
            <option value="price">Prix ↑</option>
            <option value="recent">Plus récentes</option>
          </select>
        </label>

      </div>

      <div v-if="loading" class="text-center text-slate-500 py-12">Chargement…</div>

      <div v-else-if="error" class="rounded-xl border border-rose-700 bg-rose-900/20 p-4 text-rose-300">
        <p class="font-semibold">Erreur Supabase</p>
        <p class="text-sm mt-1">{{ error }}</p>
      </div>

      <div v-else-if="filtered.length === 0" class="text-center text-slate-500 py-12">
        Aucune annonce ne correspond aux filtres.
      </div>

      <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <DealCard v-for="ad in filtered" :key="ad.id" :ad="ad" @open="openAd" />
      </div>
    </main>

    <div
      v-if="selectedAdLoading"
      class="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm grid place-items-center"
    >
      <div class="text-slate-400">Chargement de l'annonce…</div>
    </div>

    <DealModal v-if="selectedAd" :ad="selectedAd" @close="closeAd" />
  </div>
</template>
