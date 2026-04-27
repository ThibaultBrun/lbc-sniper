<script setup lang="ts">
import { computed } from "vue";
import type { Ad } from "../supabase";

const props = defineProps<{ ad: Ad }>();

const score = computed(() => props.ad.deal_score ?? 0);

// Tier de la carte: pilote couleur du bandeau + libellé
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
</script>

<template>
  <article
    :class="[
      'rounded-xl border bg-slate-900/60 overflow-hidden flex flex-col transition hover:translate-y-[-2px]',
      cardBorder,
    ]"
  >
    <!-- HEADER : bandeau coloré qui hurle le verdict IA -->
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
        ⚡ électrique
      </span>
    </div>

    <!-- BODY : photo + prix côte à côte -->
    <div class="grid grid-cols-[140px_1fr] gap-3 p-3">
      <a :href="ad.url" target="_blank" rel="noopener noreferrer" class="block shrink-0">
        <div class="aspect-square rounded-lg bg-slate-800 overflow-hidden">
          <img
            v-if="ad.image_url"
            :src="ad.image_url"
            :alt="ad.subject"
            class="h-full w-full object-cover hover:scale-105 transition"
            loading="lazy"
          />
          <div
            v-else
            class="h-full w-full grid place-items-center text-slate-600 text-xs"
          >
            pas de photo
          </div>
        </div>
      </a>

      <div class="min-w-0 flex flex-col gap-1.5">
        <!-- Prix -->
        <div class="flex items-baseline gap-2">
          <div class="text-2xl font-bold tabular-nums leading-none">
            {{ priceFmt(ad.current_price) }} €
          </div>
        </div>
        <div v-if="ad.estimated_market_eur" :class="['text-xs', discountColor]">
          marché ~<span class="tabular-nums font-semibold">{{
            priceFmt(Math.round(ad.estimated_market_eur))
          }}</span> €
          <span v-if="discountPct !== null && discountPct >= 0" class="font-bold">
            (−{{ Math.round(discountPct) }}%)
          </span>
          <span v-else-if="discountPct !== null" class="font-bold">
            (+{{ Math.round(-discountPct) }}%)
          </span>
        </div>

        <!-- Identité du vehicule -->
        <div v-if="ad.brand || ad.model || ad.year" class="text-sm text-slate-200 font-medium truncate">
          {{ [ad.brand, ad.model, ad.year].filter(Boolean).join(" ") }}
        </div>

        <!-- Tags secondaires -->
        <div class="flex flex-wrap gap-1 text-[10px]">
          <span v-if="ad.size_label" class="rounded bg-slate-800 px-1.5 py-0.5 text-slate-400">
            taille {{ ad.size_label }}
          </span>
          <span v-if="ad.wheel_size" class="rounded bg-slate-800 px-1.5 py-0.5 text-slate-400">
            {{ ad.wheel_size }}
          </span>
          <span v-if="ad.frame_material" class="rounded bg-slate-800 px-1.5 py-0.5 text-slate-400">
            {{ ad.frame_material }}
          </span>
          <span
            v-if="ad.condition_score !== null"
            class="rounded bg-slate-800 px-1.5 py-0.5 text-slate-400 tabular-nums"
          >
            état {{ ad.condition_score }}
          </span>
        </div>

        <!-- Titre annonce + ville -->
        <div class="text-xs text-slate-500 line-clamp-2 mt-auto">
          {{ ad.subject }}
        </div>
        <div class="text-[10px] text-slate-600">{{ ad.city ?? "?" }}</div>
      </div>
    </div>

    <!-- ANALYSE IA : reasoning + pros + cons, toujours visibles -->
    <div v-if="ad.reasoning || ad.pros?.length || ad.cons?.length" class="px-4 pb-3 space-y-3">
      <p
        v-if="ad.reasoning"
        class="text-xs text-slate-300 leading-relaxed bg-slate-950/40 rounded p-2 border-l-2 border-slate-600"
      >
        {{ ad.reasoning }}
      </p>

      <div v-if="ad.pros?.length" class="rounded bg-emerald-500/5 border border-emerald-500/20 p-2 space-y-1">
        <div class="text-[10px] font-bold uppercase tracking-wider text-emerald-400">
          ✓ Points forts
        </div>
        <ul class="space-y-0.5">
          <li
            v-for="(p, i) in ad.pros"
            :key="`p${i}`"
            class="text-xs text-emerald-100/90 flex gap-1.5 leading-snug"
          >
            <span class="text-emerald-500 shrink-0">•</span>
            <span>{{ p }}</span>
          </li>
        </ul>
      </div>

      <div v-if="ad.cons?.length" class="rounded bg-amber-500/5 border border-amber-500/20 p-2 space-y-1">
        <div class="text-[10px] font-bold uppercase tracking-wider text-amber-400">
          ⚠ Points de vigilance
        </div>
        <ul class="space-y-0.5">
          <li
            v-for="(c, i) in ad.cons"
            :key="`c${i}`"
            class="text-xs text-amber-100/90 flex gap-1.5 leading-snug"
          >
            <span class="text-amber-500 shrink-0">•</span>
            <span>{{ c }}</span>
          </li>
        </ul>
      </div>
    </div>

    <!-- FOOTER : CTA -->
    <a
      :href="ad.url"
      target="_blank"
      rel="noopener noreferrer"
      class="mt-auto block px-4 py-2.5 text-center text-xs font-bold uppercase tracking-wider bg-slate-800 hover:bg-slate-700 text-slate-200 transition border-t border-slate-700/50"
    >
      Voir sur LeBonCoin →
    </a>
  </article>
</template>
