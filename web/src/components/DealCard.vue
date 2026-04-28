<script setup lang="ts">
import { computed } from "vue";
import type { Ad } from "../supabase";

const props = defineProps<{ ad: Ad }>();
const emit = defineEmits<{ open: [Ad] }>();

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

const cardBorder = computed(() =>
  ({
    great: "border-emerald-500/70 shadow-emerald-500/10 shadow-lg",
    good: "border-emerald-700/60",
    fair: "border-slate-700",
    poor: "border-amber-700/40",
    bad: "border-rose-800/40 opacity-80",
  })[tier.value],
);

const headerBg = computed(() =>
  ({
    great: "bg-gradient-to-r from-emerald-600 to-emerald-500 text-slate-950",
    good: "bg-gradient-to-r from-emerald-700 to-emerald-600 text-slate-50",
    fair: "bg-gradient-to-r from-slate-700 to-slate-600 text-slate-100",
    poor: "bg-gradient-to-r from-amber-700 to-amber-600 text-slate-50",
    bad: "bg-gradient-to-r from-rose-900 to-rose-800 text-rose-100",
  })[tier.value],
);

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

const hasAnalysis = computed(
  () =>
    !!props.ad.reasoning ||
    (props.ad.pros && props.ad.pros.length > 0) ||
    (props.ad.cons && props.ad.cons.length > 0),
);
</script>

<template>
  <article
    :class="[
      'rounded-xl border bg-slate-900/60 overflow-hidden flex flex-col transition hover:translate-y-[-2px]',
      cardBorder,
    ]"
  >
    <!-- HEADER : verdict IA en couleur -->
    <div :class="['px-4 py-2.5 flex items-center justify-between gap-2', headerBg]">
      <div class="flex items-baseline gap-2 min-w-0">
        <span class="text-2xl font-black tabular-nums leading-none">{{ score }}</span>
        <span class="text-xs font-bold uppercase tracking-wider opacity-90 truncate">
          {{ tierLabel }}
        </span>
      </div>
      <span
        v-if="ad.electric"
        class="text-[10px] font-black uppercase tracking-widest bg-black/20 px-1.5 py-0.5 rounded shrink-0"
      >
        ⚡
      </span>
    </div>

    <!-- IMAGE — ouvre l'analyse (la modale), pas LBC -->
    <button
      type="button"
      @click="emit('open', ad)"
      class="block w-full text-left"
      :aria-label="`Voir l'analyse de ${ad.subject}`"
    >
      <div class="aspect-[4/3] w-full bg-slate-800 overflow-hidden">
        <img
          v-if="ad.image_url"
          :src="ad.image_url"
          :alt="ad.subject"
          class="h-full w-full object-cover hover:scale-105 transition"
          loading="lazy"
        />
        <div v-else class="h-full w-full grid place-items-center text-slate-600 text-xs">
          pas de photo
        </div>
      </div>
    </button>

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

      <div v-if="ad.brand || ad.model" class="text-sm text-slate-200 font-medium truncate">
        {{ [ad.brand, ad.model, ad.year].filter(Boolean).join(" ") }}
      </div>

      <div class="flex flex-wrap gap-1 text-[10px]">
        <span v-if="ad.size_label" class="rounded bg-slate-800 px-1.5 py-0.5 text-slate-400">
          {{ ad.size_label }}
        </span>
        <span v-if="ad.wheel_size" class="rounded bg-slate-800 px-1.5 py-0.5 text-slate-400">
          {{ ad.wheel_size }}
        </span>
        <span v-if="ad.frame_material" class="rounded bg-slate-800 px-1.5 py-0.5 text-slate-400">
          {{ ad.frame_material }}
        </span>
      </div>

      <div class="text-xs text-slate-500 line-clamp-2 mt-auto pt-1">
        {{ ad.subject }}
      </div>
      <div class="text-[10px] text-slate-600">{{ ad.city ?? "?" }}</div>
    </div>

    <!-- CTA : ouvrir l'analyse -->
    <button
      v-if="hasAnalysis"
      @click="emit('open', ad)"
      class="block px-4 py-2.5 text-center text-xs font-bold uppercase tracking-wider bg-slate-800 hover:bg-emerald-600 hover:text-slate-950 text-slate-200 transition border-t border-slate-700/50"
    >
      Analyser →
    </button>
    <a
      v-else
      :href="ad.url"
      target="_blank"
      rel="noopener noreferrer"
      class="block px-4 py-2.5 text-center text-xs font-bold uppercase tracking-wider bg-slate-800 hover:bg-slate-700 text-slate-300 transition border-t border-slate-700/50"
    >
      Voir sur LeBonCoin →
    </a>
  </article>
</template>
