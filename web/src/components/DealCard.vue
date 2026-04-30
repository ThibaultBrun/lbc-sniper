<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useFavorites } from "../favorites";
import { useAuth } from "../auth";
import { hideAd, type Ad } from "../supabase";

const props = defineProps<{ ad: Ad }>();
const emit = defineEmits<{ open: [Ad]; hidden: [number] }>();

const { isFavorite, toggle } = useFavorites();
const { isAuthenticated, isAdmin, signInWithGoogle } = useAuth();
const favPending = ref(false);
const hidePending = ref(false);

const isFav = computed(() => isFavorite(props.ad.id));

async function handleFavClick(e: MouseEvent) {
  e.stopPropagation();
  if (!isAuthenticated.value) {
    // Pas connecte -> on lance le login Google
    await signInWithGoogle();
    return;
  }
  favPending.value = true;
  try {
    await toggle(props.ad.id, props.ad.current_price);
  } catch (err) {
    console.error(err);
  } finally {
    favPending.value = false;
  }
}

async function handleHideClick(e: MouseEvent) {
  e.stopPropagation();
  if (!confirm(`Masquer cette annonce du site ?\n\n"${props.ad.subject}"`)) return;
  hidePending.value = true;
  try {
    await hideAd(props.ad.id);
    emit("hidden", props.ad.id);
  } catch (err) {
    console.error(err);
    alert("Erreur lors de la suppression : " + (err as Error).message);
  } finally {
    hidePending.value = false;
  }
}

// IMAGE LAZY-LOAD : on ne monte le <img> que quand la card entre dans le viewport,
// et on fade-in quand elle est decodee. Resultat : prix/score/tags s'affichent
// instantanement, les jpegs LBC suivent dans un 2e temps.
const imgRef = ref<HTMLDivElement | null>(null);
const imgVisible = ref(false);  // true = on monte le <img>
const imgLoaded = ref(false);   // true = decode termine -> fade-in

onMounted(() => {
  if (!props.ad.image_url || !imgRef.value) return;
  if (typeof IntersectionObserver === "undefined") {
    imgVisible.value = true;
    return;
  }
  const io = new IntersectionObserver(
    (entries) => {
      for (const e of entries) {
        if (e.isIntersecting) {
          imgVisible.value = true;
          io.disconnect();
          break;
        }
      }
    },
    {
      // Anticipe le scroll : on commence a charger 200px avant que ca rentre
      // dans la fenetre, comme ca l'image est prete quand l'utilisateur arrive.
      rootMargin: "200px 0px",
    },
  );
  io.observe(imgRef.value);
  onUnmounted(() => io.disconnect());
});

const VTT_CATEGORY_LABELS: Record<string, string> = {
  xc: "XC",
  all_mountain: "Trail / AM",
  enduro: "Enduro",
  dh: "DH",
  dirt: "Dirt",
};
const vttCategoryLabel = computed(() => {
  const c = props.ad.vtt_category;
  return c ? VTT_CATEGORY_LABELS[c] ?? null : null;
});

const score = computed(() => props.ad.deal_score ?? 0);

const tier = computed(() => {
  if (score.value >= 85) return "great";
  if (score.value >= 70) return "good";
  if (score.value >= 50) return "fair";
  if (score.value >= 30) return "poor";
  return "bad";
});

const tierLabel = computed(() =>
  ({
    great: "Excellente affaire",
    good: "Bonne affaire",
    fair: "Prix du marché",
    poor: "Un peu cher",
    bad: "Surévalué",
  })[tier.value],
);

const cardBorderClass = computed(() => `tier-border-${tier.value}`);
const headerTierClass = computed(() => `tier-${tier.value}`);

// Couleur de la jauge selon le tier. On l'applique inline (Tailwind/PostCSS
// n'a pas l'air de garder les --score-color des classes tier-* au build).
const TIER_COLORS: Record<string, string> = {
  great: "#10b981",  // emerald-500
  good: "#059669",   // emerald-600
  fair: "#94a3b8",   // slate-400
  poor: "#f59e0b",   // amber-500
  bad: "#f43f5e",    // rose-500
};
const gaugeColor = computed(() => TIER_COLORS[tier.value] ?? "#94a3b8");

// Resume de l'analyse, dose selon le score :
//   >= 80 : 2 pros (le vendeur a fait un cadeau, on insiste sur le positif)
//   40-79 : 1 pro + 1 con (analyse equilibree)
//   < 40  : 2 cons (annonce surevaluee, on previent direct)
const summaryItems = computed<Array<{ kind: "pro" | "con"; text: string }>>(() => {
  const pros = props.ad.pros ?? [];
  const cons = props.ad.cons ?? [];
  const s = score.value;
  const items: Array<{ kind: "pro" | "con"; text: string }> = [];
  if (s >= 80) {
    if (pros[0]) items.push({ kind: "pro", text: pros[0] });
    if (pros[1]) items.push({ kind: "pro", text: pros[1] });
    // Si on n'a qu'un seul pro, on complete avec le 1er con plutot que de
    // laisser une seule ligne (la card serait trop courte vs ses voisines).
    if (items.length < 2 && cons[0]) items.push({ kind: "con", text: cons[0] });
  } else if (s >= 40) {
    if (pros[0]) items.push({ kind: "pro", text: pros[0] });
    if (cons[0]) items.push({ kind: "con", text: cons[0] });
  } else {
    if (cons[0]) items.push({ kind: "con", text: cons[0] });
    if (cons[1]) items.push({ kind: "con", text: cons[1] });
    if (items.length < 2 && pros[0]) items.push({ kind: "pro", text: pros[0] });
  }
  return items;
});

const priceFmt = (v: number | null) =>
  v == null ? "?" : v.toLocaleString("fr-FR");

const discountPct = computed(() => {
  const market = props.ad.estimated_market_eur;
  const price = props.ad.current_price;
  if (!market || !price) return null;
  return ((market - price) / market) * 100;
});

const discountColor = computed(() => {
  const d = discountPct.value;
  if (d === null) return "text-slate-400";
  if (d >= 30) return "text-emerald-400";
  if (d >= 10) return "text-emerald-500";
  if (d >= -10) return "text-slate-300";
  return "text-rose-400";
});

// Proxy : si on a un deal_score, l'enricher a aussi ecrit reasoning+pros+cons
// (c'est dans la meme transaction). Permet de savoir si une analyse existe
// sans charger les jsonb arrays dans le SELECT light de la liste.
const hasAnalysis = computed(() => props.ad.deal_score !== null && props.ad.deal_score !== undefined);
</script>

<template>
  <article :class="['card card-hover', cardBorderClass]">
    <!-- HEADER : verdict IA en couleur + jauge horizontale 0-100 -->
    <div :class="['px-3 pt-2 pb-2.5', headerTierClass]">
      <div class="flex items-center justify-between gap-2 mb-1.5">
        <span class="text-xs font-bold uppercase tracking-wider opacity-95 truncate">
          {{ tierLabel }}
        </span>
        <div class="flex items-center gap-1.5 shrink-0">
          <span
            v-if="ad.electric"
            class="text-[10px] font-black uppercase tracking-widest bg-black/20 px-1.5 py-0.5 rounded"
            title="Vélo électrique"
          >⚡</span>
          <span class="text-sm font-black tabular-nums leading-none opacity-95">{{ score }}</span>
        </div>
      </div>
      <!-- Jauge horizontale : couleur unique selon le tier (inline car Tailwind strip --score-color) -->
      <div class="score-gauge" role="progressbar" :aria-valuenow="score" aria-valuemin="0" aria-valuemax="100">
        <div class="score-gauge-fill" :style="{ width: `${score}%`, backgroundColor: gaugeColor }"></div>
      </div>
    </div>

    <!-- IMAGE — ouvre l'analyse (la modale), pas LBC -->
    <div class="relative">
      <button
        type="button"
        @click="emit('open', ad)"
        class="block w-full text-left"
        :aria-label="`Voir l'analyse de ${ad.subject}`"
      >
        <div ref="imgRef" class="aspect-[4/3] w-full overflow-hidden surface-muted relative">
          <img
            v-if="ad.image_url && imgVisible"
            :src="ad.image_url"
            :alt="ad.subject"
            :class="['h-full w-full object-cover hover:scale-105 transition', imgLoaded ? 'opacity-100' : 'opacity-0']"
            decoding="async"
            referrerpolicy="no-referrer"
            @load="imgLoaded = true"
            style="transition: opacity 0.25s ease, transform 0.3s ease"
          />
          <div v-else-if="!ad.image_url" class="h-full w-full grid place-items-center text-faint text-xs">
            pas de photo
          </div>
        </div>
      </button>
      <!-- Bouton favori en overlay -->
      <button
        type="button"
        @click="handleFavClick"
        :disabled="favPending"
        :class="[
          'absolute top-2 right-2 w-9 h-9 rounded-full grid place-items-center text-lg transition shadow-lg',
          isFav
            ? 'bg-rose-500 text-white hover:bg-rose-400'
            : 'bg-black/60 text-white hover:bg-black/80',
        ]"
        :aria-label="isFav ? 'Retirer des favoris' : 'Ajouter aux favoris'"
        :title="isFav ? 'Retirer des favoris' : 'Ajouter aux favoris'"
      >
        <span v-if="isFav">♥</span>
        <span v-else>♡</span>
      </button>
      <!-- Bouton admin : masquer l'annonce du site (admin uniquement) -->
      <button
        v-if="isAdmin"
        type="button"
        @click="handleHideClick"
        :disabled="hidePending"
        class="absolute top-2 left-2 w-9 h-9 rounded-full grid place-items-center text-base transition shadow-lg bg-black/60 text-white hover:bg-rose-500"
        aria-label="Masquer cette annonce (admin)"
        title="Masquer cette annonce (admin)"
      >
        🗑
      </button>
    </div>

    <!-- INFOS -->
    <div class="p-3 space-y-1.5 flex-1 flex flex-col">
      <div class="flex items-baseline justify-between gap-2">
        <div class="text-xl font-bold tabular-nums leading-none">
          {{ priceFmt(ad.current_price) }} €
        </div>
        <div v-if="ad.estimated_market_eur" :class="['text-xs font-semibold tabular-nums', discountColor]">
          <span v-if="discountPct !== null && discountPct >= 0">−{{ Math.round(discountPct) }}%</span>
          <span v-else-if="discountPct !== null">+{{ Math.round(-discountPct) }}%</span>
        </div>
      </div>

      <div v-if="ad.brand || ad.model" class="text-sm font-medium truncate">
        {{ [ad.brand, ad.model, ad.year].filter(Boolean).join(" ") }}
      </div>

      <div class="flex flex-wrap gap-1">
        <span v-if="vttCategoryLabel" class="tag-vtt-category">{{ vttCategoryLabel }}</span>
        <span v-if="ad.regyear" class="tag-strong tabular-nums">{{ ad.regyear }}</span>
        <span v-if="ad.mileage_km" class="tag tabular-nums">
          {{ ad.mileage_km.toLocaleString("fr-FR") }} km
        </span>
        <span v-if="ad.fuel" class="tag">{{ ad.fuel }}</span>
        <span v-if="ad.gearbox" class="tag">{{ ad.gearbox }}</span>
        <span v-if="ad.size_label" class="tag">{{ ad.size_label }}</span>
        <span v-if="ad.wheel_size" class="tag">{{ ad.wheel_size }}</span>
        <span v-if="ad.frame_material" class="tag">{{ ad.frame_material }}</span>
      </div>

      <!-- Resume IA, dose selon le score (>=80 : 2 pros, 40-79 : 1+1, <40 : 2 cons) -->
      <div class="mt-auto pt-1 space-y-0.5 text-xs leading-snug">
        <div
          v-for="(item, i) in summaryItems"
          :key="i"
          class="flex gap-1"
          :style="{ color: item.kind === 'pro' ? 'var(--color-accent)' : '#b45309' }"
        >
          <span class="shrink-0">{{ item.kind === 'pro' ? '✓' : '⚠' }}</span>
          <span class="line-clamp-1">{{ item.text }}</span>
        </div>
        <!-- Fallback si pas encore enrichie -->
        <div v-if="summaryItems.length === 0" class="text-subtle line-clamp-2">{{ ad.subject }}</div>
      </div>
      <div class="text-[10px] text-faint">{{ ad.city ?? "?" }}</div>
    </div>

    <!-- CTA : ouvrir l'analyse -->
    <button
      v-if="hasAnalysis"
      @click="emit('open', ad)"
      class="block px-4 py-2.5 text-center text-xs font-bold uppercase tracking-wider btn-ghost rounded-none border-t hover:!bg-emerald-600 hover:!text-slate-950"
      :style="{ borderColor: 'var(--color-border-subtle)' }"
    >
      Analyser →
    </button>
    <a
      v-else
      :href="ad.url"
      target="_blank"
      rel="noopener noreferrer"
      class="block px-4 py-2.5 text-center text-xs font-bold uppercase tracking-wider btn-ghost rounded-none border-t"
      :style="{ borderColor: 'var(--color-border-subtle)' }"
    >
      Voir l'annonce →
    </a>
  </article>
</template>
