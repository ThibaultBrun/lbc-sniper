<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getAdById, supabase, type Ad } from "./supabase";
import AuthButton from "./components/AuthButton.vue";
import DealCard from "./components/DealCard.vue";
import DealModal from "./components/DealModal.vue";
import GeoFilter, { type GeoFilterValue } from "./components/GeoFilter.vue";
import LegalPage from "./components/LegalPage.vue";
import AdminUsers from "./components/AdminUsers.vue";
import DealCardSkeleton from "./components/DealCardSkeleton.vue";
import GuidesIndex from "./components/guides/GuidesIndex.vue";
import GuideChoisirVtt from "./components/guides/GuideChoisirVtt.vue";
import GuideEnduroVsDh from "./components/guides/GuideEnduroVsDh.vue";
import GuideDecrypterAnnonce from "./components/guides/GuideDecrypterAnnonce.vue";
import SavedSearchesBar from "./components/SavedSearchesBar.vue";
import type { SavedSearchFilters } from "./saved-searches";
import { useFavorites } from "./favorites";
import { haversineKm } from "./geo";

const route = useRoute();
const router = useRouter();

// Mode "secret" si l'URL commence par /secret. La home publique restreint
// par defaut aux categories VTT (enduro + DH).
const isSecret = computed(() => route.path.startsWith("/secret"));

const isLegalPage = computed(() =>
  ["about", "legal", "privacy", "tos"].includes(String(route.name)),
);

const isAdminPage = computed(() => route.name === "admin-users");

const isGuidesIndex = computed(() => route.name === "guides-index");
const isGuideChoisir = computed(() => route.name === "guide-choisir");
const isGuideEnduroVsDh = computed(() => route.name === "guide-enduro-vs-dh");
const isGuideDecrypter = computed(() => route.name === "guide-decrypter");

const isFavoritesPage = computed(() => route.name === "favorites");

// Favoris : filtre les ads qu'on affiche aux ID en favori du user.
const { favoriteIds } = useFavorites();

// Toutes les annonces classifiees comme VTT par le scraper. La home publique
// les expose toutes ; le filtre UI "Type" (vtt_category) permet ensuite de
// trier par usage (XC, all-mountain, enduro, DH, dirt).
const VTT_LABELS = ["VTT enduro", "VTT DH", "VTT XC", "VTT dirt"];

// Encart guides : replie par defaut sur mobile (gain de place), deplie sur desktop.
// L'utilisateur peut basculer manuellement.
const guidesOpen = ref(typeof window !== "undefined" && window.innerWidth >= 640);
function toggleGuides() {
  guidesOpen.value = !guidesOpen.value;
}

const ads = ref<Ad[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);
// Compteurs globaux (toutes annonces actives du scope, pas juste les 50 chargees).
// Charges en parallele du SELECT principal via 3 count queries server-side.
const totalCount = ref(0);
const enrichedCount = ref(0);
const greatCount = ref(0);
const sortBy = ref<"deal" | "price" | "recent">("deal");
const categoryFilter = ref<string | null>(null);
const vttCategoryFilter = ref<string | null>(null);

const geo = ref<GeoFilterValue | null>(null);
const radiusKm = ref(50);
const electricFilter = ref<"all" | "yes" | "no">("all");

// Categories d'usage VTT (cle = valeur enum SQL, label = ce qu'on affiche).
// Trail et all-mountain sont fusionnees en pratique sur le marche FR.
const VTT_CATEGORY_OPTIONS = [
  { value: "xc", label: "XC / Cross-country" },
  { value: "all_mountain", label: "Trail / All-mountain" },
  { value: "enduro", label: "Enduro" },
  { value: "dh", label: "DH / Descente" },
  { value: "dirt", label: "Dirt" },
];
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
  // On NE prend PAS l'objet de la liste tel quel : il vient du SELECT light
  // (sans reasoning / pros / cons / attributes / body complet). On utilise
  // l'objet light comme placeholder visuel pendant le re-fetch complet
  // pour eviter le flash "loading", puis on remplace.
  const fromList = ads.value.find((a) => a.id === adId);
  if (fromList) {
    selectedAd.value = fromList;
  } else {
    selectedAdLoading.value = true;
  }
  try {
    const full = await getAdById(adId);
    if (full) selectedAd.value = full;
  } catch (e) {
    console.error("Failed to fetch ad", adId, e);
    if (!fromList) selectedAd.value = null;
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

// Suppression admin reussie : on retire l'ad de la liste localement (pas de
// reload pour l'experience instantanee) et on decremente le total.
function handleAdHidden(adId: number) {
  ads.value = ads.value.filter((a) => a.id !== adId);
  if (totalCount.value > 0) totalCount.value -= 1;
}

function closeAd() {
  router.push({ name: isSecret.value ? "secret" : "home" });
}

watch(() => route.params.id, syncSelectedFromRoute);
watch(isSecret, () => {
  // Reset le filtre catégorie quand on bascule de mode (les options changent)
  categoryFilter.value = null;
});

// Champs strict minimum pour la liste / DealCard / filtres geo+prix+electric.
// On EXCLUT explicitement (rechargees via getAdById a l'ouverture de la modale) :
//   - body (texte long, plombe la requete 4x plus que le reste)
//   - reasoning, pros, cons (jsonb arrays, ~500o-2ko par ad)
//   - attributes (jsonb), enriched_at, enrich_error, enrich_model
//   - watch_id, category_id, category_name (admin uniquement)
//   - zipcode, first_publication, last_seen_at, condition_score, is_active (pas affiche)
const LIST_FIELDS = [
  "id", "subject", "url", "image_url", "city",
  "ad_lat", "ad_lng", "category_label",
  "current_price", "first_seen_at", "estimated_market_eur",
  "mileage_km", "fuel", "gearbox", "regyear",
  "brand", "model", "year", "frame_material", "wheel_size", "electric",
  "size_label", "vtt_category", "deal_score",
].join(",");

// Helper : applique le scope commun (is_active + admin_hidden=false + VTT).
// `admin_hidden=true` = annonce masquee par un admin ; jamais retouchee par le
// scraper, donc la suppression est definitive meme si LBC reposte l'annonce.
function scopedQuery() {
  let q = supabase.from("listings").select("*", { count: "exact", head: true })
    .eq("is_active", true)
    .eq("admin_hidden", false);
  if (!isSecret.value) q = q.in("category_label", VTT_LABELS);
  return q;
}

// Page initiale chargee tres vite (100 ads = 5 lignes en xl). Les filtres
// client-side ne fonctionnent que sur ce qu'on a charge — on complete en
// background avec _loadRest pour avoir le dataset entier.
const INITIAL_PAGE_SIZE = 100;
const FULL_PAGE_SIZE = 1000;

function buildListQuery() {
  let q = supabase
    .from("listings")
    .select(LIST_FIELDS)
    .eq("is_active", true)
    .eq("admin_hidden", false);
  if (!isSecret.value) q = q.in("category_label", VTT_LABELS);
  return q.order("deal_score", { ascending: false, nullsFirst: false });
}

const fullDatasetLoaded = ref(false);

async function load() {
  loading.value = true;
  error.value = null;
  fullDatasetLoaded.value = false;
  try {
    // Phase 1 : on attend SEULEMENT la 1ere page (100 ads) + les 3 counts.
    // L'UI peut s'afficher des qu'on a ca (~150-300ms vs 575ms avant).
    const [listRes, totalRes, enrichedRes, greatRes] = await Promise.all([
      buildListQuery().limit(INITIAL_PAGE_SIZE),
      scopedQuery(),
      scopedQuery().not("deal_score", "is", null),
      scopedQuery().gte("deal_score", 80),
    ]);
    if (listRes.error) throw listRes.error;
    ads.value = listRes.data as unknown as Ad[];
    totalCount.value = totalRes.count ?? 0;
    enrichedCount.value = enrichedRes.count ?? 0;
    greatCount.value = greatRes.count ?? 0;
  } catch (e: any) {
    error.value = e.message ?? String(e);
  } finally {
    loading.value = false;
  }
  await syncSelectedFromRoute();

  // Phase 2 : en background, complete le dataset jusqu'a 1000 si necessaire
  // (pour les filtres geo/prix/electric qui ont besoin du dataset entier).
  // Pas de await en haut : l'UI affiche deja les 100 premieres.
  if (totalCount.value > INITIAL_PAGE_SIZE) {
    _loadRest();
  } else {
    fullDatasetLoaded.value = true;
  }
}

async function _loadRest() {
  try {
    const { data, error: e } = await buildListQuery()
      .range(INITIAL_PAGE_SIZE, FULL_PAGE_SIZE - 1);
    if (e) {
      console.error("Background load failed:", e);
      return;
    }
    if (data && data.length > 0) {
      // On concatene en preservant l'ordre serveur (deja triE par deal_score).
      ads.value = [...ads.value, ...(data as unknown as Ad[])];
    }
    fullDatasetLoaded.value = true;
  } catch (e) {
    console.error("Background load failed:", e);
  }
}

// Quand on bascule entre / et /secret, on recharge avec le bon scope.
watch(isSecret, () => {
  load();
});

onMounted(async () => {
  syncSelectedFromRoute();
  await load();
});

// Le filtrage de scope (VTT only / tout) est deja fait cote serveur dans
// load(). On considere donc ads.value comme deja "scoped".
const categories = computed(() => {
  const set = new Set(
    ads.value.map((a) => a.category_label).filter((c): c is string => !!c),
  );
  return Array.from(set).sort();
});

const currentFilters = computed<SavedSearchFilters>(() => ({
  categoryFilter: categoryFilter.value,
  vttCategoryFilter: vttCategoryFilter.value,
  geo: geo.value,
  radiusKm: radiusKm.value,
  electricFilter: electricFilter.value,
  priceMin: priceMin.value,
  priceMax: priceMax.value,
  searchText: searchText.value,
  sortBy: sortBy.value,
}));

function applySavedSearch(f: SavedSearchFilters) {
  categoryFilter.value = f.categoryFilter;
  vttCategoryFilter.value = f.vttCategoryFilter ?? null;
  geo.value = f.geo;
  radiusKm.value = f.radiusKm ?? 50;
  electricFilter.value = f.electricFilter ?? "all";
  priceMin.value = f.priceMin ?? null;
  priceMax.value = f.priceMax ?? null;
  searchText.value = f.searchText ?? "";
  sortBy.value = f.sortBy ?? "deal";
}

function resetFilters() {
  categoryFilter.value = null;
  vttCategoryFilter.value = null;
  geo.value = null;
  radiusKm.value = 50;
  electricFilter.value = "all";
  priceMin.value = null;
  priceMax.value = null;
  searchText.value = "";
  sortBy.value = "deal";
}

// True des qu'au moins un filtre est actif (utilise pour afficher le bouton reset).
const hasActiveFilters = computed(() =>
  categoryFilter.value !== null
  || vttCategoryFilter.value !== null
  || geo.value !== null
  || electricFilter.value !== "all"
  || priceMin.value !== null
  || priceMax.value !== null
  || searchText.value !== ""
  || sortBy.value !== "deal",
);

const filtered = computed(() => {
  let list = ads.value;
  // Page /favoris : on garde uniquement les annonces favorites du user
  if (isFavoritesPage.value) {
    list = list.filter((a) => favoriteIds.value.has(a.id));
  }
  if (categoryFilter.value)
    list = list.filter((a) => a.category_label === categoryFilter.value);

  if (vttCategoryFilter.value)
    list = list.filter((a) => a.vtt_category === vttCategoryFilter.value);

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

  // Filtre recherche texte — desormais sur le titre uniquement (le body
  // n'est plus charge dans le payload initial pour gagner ~70% sur la
  // requete Supabase). Si tu veux chercher dans la description, ouvre
  // l'analyse (modale) qui contient le body complet.
  const q = normalizeText(searchText.value.trim());
  if (q.length > 0) {
    list = list.filter((a) => {
      const haystack = normalizeText(a.subject ?? "");
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
  [categoryFilter, vttCategoryFilter, electricFilter, priceMin, priceMax, geo, radiusKm, sortBy, pageSize, searchText],
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

// Stats globales, pas calculees depuis ads.value (qui est tronque a 50)
// mais depuis les count queries lancees dans load().
const stats = computed(() => ({
  total: totalCount.value,
  enriched: enrichedCount.value,
  great: greatCount.value,
}));
</script>

<template>
  <LegalPage v-if="isLegalPage" />
  <AdminUsers v-else-if="isAdminPage" />
  <GuidesIndex v-else-if="isGuidesIndex" />
  <GuideChoisirVtt v-else-if="isGuideChoisir" />
  <GuideEnduroVsDh v-else-if="isGuideEnduroVsDh" />
  <GuideDecrypterAnnonce v-else-if="isGuideDecrypter" />
  <div v-else class="min-h-screen flex flex-col">
    <header class="surface-header">
      <div class="max-w-7xl mx-auto px-4 sm:px-6 py-3 sm:py-4 flex flex-wrap items-center gap-3 sm:gap-4 justify-between">
        <div class="min-w-0">
          <h1 class="text-lg sm:text-xl font-bold tracking-tight">
            <span style="color: var(--color-accent-hover)">Trouve</span> Ton VTT
            <span v-if="isSecret" class="ml-2 text-[10px] sm:text-xs font-normal uppercase tracking-wider" style="color: var(--color-danger-text)">[ secret ]</span>
          </h1>
          <p class="text-[11px] sm:text-xs text-muted mt-0.5 hidden sm:block">
            <span v-if="isSecret">VTT, voitures, motos — analyse IA complète</span>
            <span v-else>les meilleures affaires VTT du moment, analysées par IA</span>
          </p>
        </div>
        <div class="flex items-center gap-2 sm:gap-4 text-xs text-muted flex-wrap justify-end">
          <!-- Stats : forme compacte sur mobile, detaillee en desktop -->
          <span class="sm:hidden text-[11px]">
            <span class="font-semibold" style="color: var(--color-accent-hover)">{{ stats.great }}</span>
            / {{ stats.enriched }} ex.
          </span>
          <router-link to="/guides" class="font-medium hover:opacity-80 hidden lg:inline" style="color: var(--color-accent-hover)">
            📘 Guides
          </router-link>
          <span class="hidden sm:inline" v-if="filtered.length === stats.total">{{ stats.total }} annonces</span>
          <span class="hidden sm:inline" v-else>{{ filtered.length }} / {{ stats.total }} annonces</span>
          <span class="hidden md:inline">{{ stats.enriched }} analysées</span>
          <span class="hidden sm:inline font-semibold" style="color: var(--color-accent-hover)">{{ stats.great }} excellentes</span>
          <button @click="load" class="btn btn-ghost" aria-label="Recharger">
            <span class="sm:hidden">↻</span>
            <span class="hidden sm:inline">↻ Recharger</span>
          </button>
          <AuthButton />
        </div>
      </div>
    </header>

    <main class="max-w-7xl mx-auto px-4 sm:px-6 py-4 sm:py-6 space-y-4 sm:space-y-6 w-full">
      <!-- Banniere /favoris -->
      <div v-if="isFavoritesPage" class="banner-info">
        <div>
          <div class="text-lg font-bold" style="color: var(--color-danger-text)">♥ Mes favoris</div>
          <div class="text-xs" style="color: var(--color-danger-text); opacity: 0.7">
            Annonces que tu as marquées avec le cœur. Tu seras notifié si leur prix baisse.
          </div>
        </div>
        <router-link to="/" class="btn btn-ghost">← Retour à toutes les annonces</router-link>
      </div>

      <!-- Encart guides : visible sur la home publique uniquement, pas sur /secret ni /favoris.
           Replie par defaut sur mobile (chevron pour deplier). -->
      <section v-if="!isSecret && !isFavoritesPage" class="guides-banner">
        <button
          type="button"
          @click="toggleGuides"
          class="w-full flex items-baseline justify-between gap-3 text-left"
          :aria-expanded="guidesOpen"
        >
          <div class="min-w-0 flex-1">
            <h2 class="text-sm sm:text-base font-bold flex items-center gap-2">
              <span class="transition-transform inline-block" :style="{ transform: guidesOpen ? 'rotate(90deg)' : 'rotate(0deg)' }">▸</span>
              📘 Avant d'acheter, lis nos guides
            </h2>
            <p v-if="guidesOpen" class="text-xs text-muted mt-0.5 ml-5">
              Conseils pratiques pour choisir, négocier et éviter les arnaques.
            </p>
          </div>
          <router-link
            to="/guides"
            @click.stop
            class="text-xs font-semibold whitespace-nowrap shrink-0"
            style="color: var(--color-accent-hover)"
          >
            Tous →
          </router-link>
        </button>
        <div v-if="guidesOpen" class="grid gap-3 sm:grid-cols-3 mt-4">
          <router-link to="/guides/comment-choisir-vtt-occasion" class="guide-mini-card">
            <div class="text-xl">🛒</div>
            <div class="font-semibold leading-tight">Choisir un VTT d'occasion</div>
            <div class="text-xs text-muted">Checklist mécanique, signaux d'alerte, négociation.</div>
            <div class="text-[10px] text-subtle">⏱ 8 min</div>
          </router-link>
          <router-link to="/guides/enduro-vs-dh-vs-all-mountain" class="guide-mini-card">
            <div class="text-xl">🚵</div>
            <div class="font-semibold leading-tight">Enduro, DH, all-mountain ?</div>
            <div class="text-xs text-muted">Quelle catégorie pour quel terrain.</div>
            <div class="text-[10px] text-subtle">⏱ 6 min</div>
          </router-link>
          <router-link to="/guides/decrypter-annonce-leboncoin" class="guide-mini-card">
            <div class="text-xl">🕵</div>
            <div class="font-semibold leading-tight">Décrypter une annonce LBC</div>
            <div class="text-xs text-muted">Reconnaître les arnaques et vélos volés.</div>
            <div class="text-[10px] text-subtle">⏱ 7 min</div>
          </router-link>
        </div>
      </section>

      <!-- Filtres -->
      <div class="surface-filters">

        <!-- Ligne 1 : recherche texte + ville/position/rayon -->
        <div class="flex flex-wrap items-center gap-4">
          <label class="flex items-center gap-2 flex-1 min-w-[260px]">
            <span class="text-muted whitespace-nowrap">🔎</span>
            <input
              v-model="searchText"
              type="search"
              placeholder="Rechercher dans les titres…"
              class="input-base flex-1"
            />
          </label>

          <GeoFilter v-model="geo" v-model:radius-km="radiusKm" />
        </div>

        <!-- Ligne 2 : filtres metier -->
        <div class="flex flex-wrap items-center gap-4 pt-3" style="border-top: 1px solid var(--color-border-subtle)">
          <label v-if="categories.length > 1" class="flex items-center gap-2">
            <span class="text-muted">Catégorie:</span>
            <select v-model="categoryFilter" class="input-base">
              <option :value="null">Toutes</option>
              <option v-for="c in categories" :key="c" :value="c">{{ c }}</option>
            </select>
          </label>

          <label class="flex items-center gap-2">
            <span class="text-muted">🚵 Type:</span>
            <select v-model="vttCategoryFilter" class="input-base">
              <option :value="null">Tous</option>
              <option v-for="o in VTT_CATEGORY_OPTIONS" :key="o.value" :value="o.value">
                {{ o.label }}
              </option>
            </select>
          </label>

          <label class="flex items-center gap-2">
            <span class="text-muted">⚡ Électrique:</span>
            <select v-model="electricFilter" class="input-base">
              <option value="all">Tous</option>
              <option value="yes">Électrique</option>
              <option value="no">Musculaire</option>
            </select>
          </label>

          <label class="flex items-center gap-1.5">
            <span class="text-muted">Prix:</span>
            <input
              v-model.number="priceMin"
              type="number"
              min="0"
              placeholder="min"
              class="input-base w-24 text-right tabular-nums"
            />
            <span class="text-subtle">–</span>
            <input
              v-model.number="priceMax"
              type="number"
              min="0"
              placeholder="max"
              class="input-base w-24 text-right tabular-nums"
            />
            <span class="text-subtle">€</span>
          </label>

          <label class="flex items-center gap-2">
            <span class="text-muted">Tri:</span>
            <select v-model="sortBy" class="input-base">
              <option value="deal">Score IA ↓</option>
              <option value="price">Prix ↑</option>
              <option value="recent">Plus récentes</option>
            </select>
          </label>

          <div class="ml-auto flex items-center gap-2">
            <button v-if="hasActiveFilters" @click="resetFilters" class="btn btn-ghost"
              title="Reinitialiser tous les filtres"
            >
              ✕ Reset
            </button>
            <SavedSearchesBar :current-filters="currentFilters" @apply="applySavedSearch" />
          </div>
        </div>
      </div>

      <!-- Skeleton pendant chargement initial : meme grille, meme nb par page -->
      <div v-if="loading" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <DealCardSkeleton v-for="i in pageSize" :key="`sk${i}`" />
      </div>

      <div v-else-if="error" class="panel-error">
        <p class="font-semibold">Erreur Supabase</p>
        <p class="text-sm mt-1">{{ error }}</p>
      </div>

      <div v-else-if="filtered.length === 0" class="text-center text-subtle py-12">
        Aucune annonce ne correspond aux filtres.
      </div>

      <div v-else>
        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          <DealCard v-for="ad in paginated" :key="ad.id" :ad="ad" @open="openAd" @hidden="handleAdHidden" />
        </div>

        <!-- Pagination -->
        <nav v-if="totalPages > 1" class="mt-8 flex items-center justify-center gap-1" aria-label="Pagination">
          <button @click="goPage(currentPage - 1)" :disabled="currentPage === 1" class="page-btn">
            ‹ Précédent
          </button>

          <template v-for="(p, i) in pageNumbers" :key="`p${i}`">
            <span v-if="p === '…'" class="px-2 text-subtle">…</span>
            <button
              v-else
              @click="goPage(p)"
              :class="p === currentPage ? 'page-btn-active' : 'page-btn'"
            >
              {{ p }}
            </button>
          </template>

          <button @click="goPage(currentPage + 1)" :disabled="currentPage === totalPages" class="page-btn">
            Suivant ›
          </button>
        </nav>

        <p class="mt-3 text-center text-xs text-subtle tabular-nums">
          {{ filtered.length }} annonce{{ filtered.length > 1 ? "s" : "" }}
          <span v-if="totalPages > 1"> · page {{ currentPage }} / {{ totalPages }}</span>
        </p>
      </div>
    </main>

    <div v-if="selectedAdLoading" class="modal-backdrop">
      <div class="text-muted">Chargement de l'annonce…</div>
    </div>

    <DealModal v-if="selectedAd" :ad="selectedAd" @close="closeAd" />

    <footer class="surface-footer">
      <div class="space-x-4">
        <router-link to="/guides" class="hover:opacity-80">Guides</router-link>
        <router-link to="/a-propos" class="hover:opacity-80">À propos</router-link>
        <router-link to="/mentions-legales" class="hover:opacity-80">Mentions légales</router-link>
        <router-link to="/confidentialite" class="hover:opacity-80">Confidentialité</router-link>
        <router-link to="/cgu" class="hover:opacity-80">CGU</router-link>
      </div>
      <p class="mt-2 text-[10px] text-faint">
        Trouve Ton VTT n'est pas affilié à Leboncoin. Analyses générées par IA, à titre indicatif.
      </p>
    </footer>
  </div>
</template>
