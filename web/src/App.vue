<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getAdById, supabase, type Ad } from "./supabase";
import DealCard from "./components/DealCard.vue";
import DealModal from "./components/DealModal.vue";
import GeoFilter, { type GeoFilterValue } from "./components/GeoFilter.vue";
import LegalPage from "./components/LegalPage.vue";
import { haversineKm } from "./geo";

const route = useRoute();
const router = useRouter();

// Mode "secret" si l'URL commence par /secret. La home publique restreint
// par defaut aux categories VTT (enduro + DH).
const isSecret = computed(() => route.path.startsWith("/secret"));

const isLegalPage = computed(() =>
  ["about", "legal", "privacy", "tos"].includes(String(route.name)),
);

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
const searchText = ref("");

function normalizeText(s: string): string {
  return s
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

// Pagination : 5 lignes d'annonces par page. Le nombre de colonnes (donc la
// taille de page) suit les breakpoints Tailwind utilises sur la grille.
const ROWS_PER_PAGE = 5;
const cols = ref(1);
const currentPage = ref(1);

function updateCols() {
  if (typeof window === "undefined") return;
  const w = window.innerWidth;
  if (w >= 1280) cols.value = 4;        // xl: 4 colonnes
  else if (w >= 1024) cols.value = 3;   // lg: 3
  else if (w >= 640) cols.value = 2;    // sm: 2
  else cols.value = 1;
}

const pageSize = computed(() => ROWS_PER_PAGE * cols.value);

onMounted(() => {
  updateCols();
  window.addEventListener("resize", updateCols);
});
onUnmounted(() => {
  if (typeof window !== "undefined") window.removeEventListener("resize", updateCols);
});

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
    // On charge uniquement ce qui est utile pour la liste + le filtrage.
    // Les gros champs (attributes jsonb, reasoning, pros/cons jsonb) ne
    // sont pas utilises par les cards et seront recharges quand l'utilisateur
    // ouvre la modale (via getAdById qui fait un select * cible).
    const LIST_FIELDS = [
      "id", "watch_id", "subject", "body", "url", "image_url",
      "city", "zipcode", "ad_lat", "ad_lng",
      "category_id", "category_name", "category_label",
      "current_price", "first_publication", "first_seen_at", "last_seen_at",
      "is_active", "mileage_km", "fuel", "gearbox", "regyear",
      "brand", "model", "year", "frame_material", "wheel_size", "electric",
      "size_label", "condition_score", "estimated_market_eur", "deal_score",
      "enriched_at", "enrich_error",
    ].join(",");
    const { data, error: e } = await supabase
      .from("ads")
      .select(LIST_FIELDS)
      .eq("is_active", true)
      .order("deal_score", { ascending: false, nullsFirst: false })
      .limit(1000);
    if (e) throw e;
    // Les gros champs manquants seront a null/undefined; le type Ad reste
    // satisfait via assertion (DealCard ne les utilise pas).
    ads.value = data as unknown as Ad[];
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

  // Filtre recherche texte (subject + body) — live, insensible casse/accents
  const q = normalizeText(searchText.value.trim());
  if (q.length > 0) {
    list = list.filter((a) => {
      const haystack = normalizeText(`${a.subject ?? ""} ${a.body ?? ""}`);
      return haystack.includes(q);
    });
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

const totalPages = computed(() =>
  Math.max(1, Math.ceil(filtered.value.length / pageSize.value)),
);

const paginated = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return filtered.value.slice(start, start + pageSize.value);
});

// Reset a la page 1 quand les filtres changent ou que la taille de page bouge.
watch(
  [categoryFilter, electricFilter, priceMin, priceMax, geo, radiusKm, sortBy, pageSize, searchText],
  () => {
    currentPage.value = 1;
  },
);

// Si le total de pages descend en-dessous de la page courante (filtre plus
// restrictif appliqué), on clamp.
watch(totalPages, (n) => {
  if (currentPage.value > n) currentPage.value = n;
});

function goPage(p: number) {
  currentPage.value = Math.min(Math.max(1, p), totalPages.value);
  // Remonter en haut pour que l'utilisateur voie les nouvelles annonces.
  window.scrollTo({ top: 0, behavior: "smooth" });
}

// Compresse la liste des pages affichées : 1 ... 4 5 6 ... 12
const pageNumbers = computed<(number | "…")[]>(() => {
  const total = totalPages.value;
  const cur = currentPage.value;
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1);
  const result: (number | "…")[] = [1];
  if (cur > 3) result.push("…");
  for (let i = Math.max(2, cur - 1); i <= Math.min(total - 1, cur + 1); i++) {
    result.push(i);
  }
  if (cur < total - 2) result.push("…");
  result.push(total);
  return result;
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
  <LegalPage v-if="isLegalPage" />
  <div v-else class="min-h-screen flex flex-col">
    <header class="border-b border-slate-800 bg-slate-900/40 backdrop-blur sticky top-0 z-10">
      <div class="max-w-7xl mx-auto px-6 py-4 flex flex-wrap items-baseline gap-4 justify-between">
        <div>
          <h1 class="text-xl font-bold tracking-tight">
            <span class="text-emerald-400">Trouve</span> Ton VTT
            <span v-if="isSecret" class="ml-2 text-xs font-normal text-rose-400 uppercase tracking-wider">[ secret ]</span>
          </h1>
          <p class="text-xs text-slate-400 mt-0.5">
            <span v-if="isSecret">VTT, voitures, motos — analyse IA complète</span>
            <span v-else>les meilleures affaires VTT du moment, analysées par IA</span>
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
      <div class="space-y-3 text-sm rounded-xl border border-slate-800 bg-slate-900/40 p-4">

        <!-- Ligne 1 : recherche texte + ville/position/rayon -->
        <div class="flex flex-wrap items-center gap-4">
          <label class="flex items-center gap-2 flex-1 min-w-[260px]">
            <span class="text-slate-400 whitespace-nowrap">🔎</span>
            <input
              v-model="searchText"
              type="search"
              placeholder="Rechercher (titre, description)…"
              class="flex-1 bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-slate-100 placeholder:text-slate-500 focus:border-emerald-500 focus:outline-none"
            />
          </label>

          <GeoFilter
            v-model="geo"
            v-model:radius-km="radiusKm"
          />
        </div>

        <!-- Ligne 2 : filtres metier -->
        <div class="flex flex-wrap items-center gap-4 pt-3 border-t border-slate-800/60">
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
      </div>

      <div v-if="loading" class="text-center text-slate-500 py-12">Chargement…</div>

      <div v-else-if="error" class="rounded-xl border border-rose-700 bg-rose-900/20 p-4 text-rose-300">
        <p class="font-semibold">Erreur Supabase</p>
        <p class="text-sm mt-1">{{ error }}</p>
      </div>

      <div v-else-if="filtered.length === 0" class="text-center text-slate-500 py-12">
        Aucune annonce ne correspond aux filtres.
      </div>

      <div v-else>
        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          <DealCard v-for="ad in paginated" :key="ad.id" :ad="ad" @open="openAd" />
        </div>

        <!-- Pagination -->
        <nav
          v-if="totalPages > 1"
          class="mt-8 flex items-center justify-center gap-1 text-sm"
          aria-label="Pagination"
        >
          <button
            @click="goPage(currentPage - 1)"
            :disabled="currentPage === 1"
            class="rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed px-3 py-1.5 text-slate-200 transition"
          >
            ‹ Précédent
          </button>

          <template v-for="(p, i) in pageNumbers" :key="`p${i}`">
            <span
              v-if="p === '…'"
              class="px-2 text-slate-500"
            >…</span>
            <button
              v-else
              @click="goPage(p)"
              :class="[
                'rounded px-3 py-1.5 transition tabular-nums',
                p === currentPage
                  ? 'bg-emerald-500 text-slate-950 font-bold'
                  : 'bg-slate-800 hover:bg-slate-700 text-slate-200',
              ]"
            >
              {{ p }}
            </button>
          </template>

          <button
            @click="goPage(currentPage + 1)"
            :disabled="currentPage === totalPages"
            class="rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed px-3 py-1.5 text-slate-200 transition"
          >
            Suivant ›
          </button>
        </nav>

        <p class="mt-3 text-center text-xs text-slate-500 tabular-nums">
          {{ filtered.length }} annonce{{ filtered.length > 1 ? "s" : "" }}
          <span v-if="totalPages > 1"> · page {{ currentPage }} / {{ totalPages }}</span>
        </p>
      </div>
    </main>

    <div
      v-if="selectedAdLoading"
      class="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm grid place-items-center"
    >
      <div class="text-slate-400">Chargement de l'annonce…</div>
    </div>

    <DealModal v-if="selectedAd" :ad="selectedAd" @close="closeAd" />

    <footer class="border-t border-slate-800 mt-auto py-4 text-center text-xs text-slate-500">
      <div class="space-x-4">
        <router-link to="/a-propos" class="hover:text-slate-300">À propos</router-link>
        <router-link to="/mentions-legales" class="hover:text-slate-300">Mentions légales</router-link>
        <router-link to="/confidentialite" class="hover:text-slate-300">Confidentialité</router-link>
        <router-link to="/cgu" class="hover:text-slate-300">CGU</router-link>
      </div>
      <p class="mt-2 text-[10px] text-slate-600">
        Trouve Ton VTT n'est pas affilié à Leboncoin. Analyses générées par IA, à titre indicatif.
      </p>
    </footer>
  </div>
</template>
