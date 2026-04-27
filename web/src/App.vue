<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getAdById, supabase, type Ad } from "./supabase";
import DealCard from "./components/DealCard.vue";
import DealModal from "./components/DealModal.vue";

const route = useRoute();
const router = useRouter();

const ads = ref<Ad[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
const minScore = ref(60);
const sortBy = ref<"deal" | "price" | "recent">("deal");
const watchFilter = ref<string | null>(null);
const showUnenriched = ref(false);

// L'annonce affichée dans la modale est dérivée de l'URL.
// Si l'annonce est dans la liste mémo, on l'utilise direct ; sinon
// on la fetch en standalone (utile quand quelqu'un arrive via lien partagé).
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
  router.push({ name: "ad", params: { id: ad.id } });
}

function closeAd() {
  router.push({ name: "home" });
}

watch(() => route.params.id, syncSelectedFromRoute);

async function load() {
  loading.value = true;
  error.value = null;
  try {
    const { data, error: e } = await supabase
      .from("ads")
      .select("*")
      .eq("is_active", true)
      .order("deal_score", { ascending: false, nullsFirst: false })
      .limit(500);
    if (e) throw e;
    ads.value = data as Ad[];
  } catch (e: any) {
    error.value = e.message ?? String(e);
  } finally {
    loading.value = false;
  }
  // Une fois la liste chargée, on resync la modale (si l'URL pointe sur une annonce
  // qui est dans la liste, on l'utilise telle quelle plutôt que de refetch).
  await syncSelectedFromRoute();
}

onMounted(async () => {
  // Lance la requête modale en parallèle de la liste (utile quand quelqu'un
  // arrive direct sur /ad/:id, on ne veut pas attendre la liste pour afficher).
  syncSelectedFromRoute();
  await load();
});

const watches = computed(() => {
  const set = new Set(ads.value.map((a) => a.watch_id));
  return Array.from(set).sort();
});

const filtered = computed(() => {
  let list = ads.value;
  if (watchFilter.value) list = list.filter((a) => a.watch_id === watchFilter.value);
  if (!showUnenriched.value) list = list.filter((a) => a.deal_score !== null);
  list = list.filter((a) => (a.deal_score ?? -1) >= minScore.value || a.deal_score === null && showUnenriched.value);

  if (sortBy.value === "deal") {
    list = [...list].sort((a, b) => (b.deal_score ?? -1) - (a.deal_score ?? -1));
  } else if (sortBy.value === "price") {
    list = [...list].sort((a, b) => (a.current_price ?? Infinity) - (b.current_price ?? Infinity));
  } else {
    list = [...list].sort(
      (a, b) => new Date(b.first_seen_at).getTime() - new Date(a.first_seen_at).getTime(),
    );
  }
  return list;
});

const stats = computed(() => {
  const all = ads.value;
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
          </h1>
          <p class="text-xs text-slate-400 mt-0.5">
            les meilleures affaires du Bon Coin, analysées par IA
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
        <label class="flex items-center gap-2">
          <span class="text-slate-400">Recherche:</span>
          <select
            v-model="watchFilter"
            class="bg-slate-800 border border-slate-700 rounded px-2 py-1 text-slate-100"
          >
            <option :value="null">Toutes</option>
            <option v-for="w in watches" :key="w" :value="w">{{ w }}</option>
          </select>
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

        <label class="flex items-center gap-2 flex-1 min-w-[200px]">
          <span class="text-slate-400 whitespace-nowrap">Score min: <b class="text-emerald-400 tabular-nums">{{ minScore }}</b></span>
          <input
            v-model.number="minScore"
            type="range"
            min="0"
            max="100"
            class="flex-1 accent-emerald-500"
          />
        </label>

        <label class="flex items-center gap-2 cursor-pointer select-none">
          <input v-model="showUnenriched" type="checkbox" class="accent-emerald-500" />
          <span class="text-slate-400">Inclure non-analysées</span>
        </label>
      </div>

      <!-- États -->
      <div v-if="loading" class="text-center text-slate-500 py-12">
        Chargement…
      </div>

      <div
        v-else-if="error"
        class="rounded-xl border border-rose-700 bg-rose-900/20 p-4 text-rose-300"
      >
        <p class="font-semibold">Erreur Supabase</p>
        <p class="text-sm mt-1">{{ error }}</p>
        <p class="text-xs mt-2 text-rose-400/70">
          Vérifie <code>web/.env</code> et que le SQL schema est bien appliqué.
        </p>
      </div>

      <div v-else-if="filtered.length === 0" class="text-center text-slate-500 py-12">
        Aucune annonce ne correspond aux filtres.
      </div>

      <div
        v-else
        class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
      >
        <DealCard
          v-for="ad in filtered"
          :key="ad.id"
          :ad="ad"
          @open="openAd"
        />
      </div>
    </main>

    <!-- Loader plein écran si on attend l'annonce ciblée par l'URL -->
    <div
      v-if="selectedAdLoading"
      class="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm grid place-items-center"
    >
      <div class="text-slate-400">Chargement de l'annonce…</div>
    </div>

    <DealModal
      v-if="selectedAd"
      :ad="selectedAd"
      @close="closeAd"
    />
  </div>
</template>
