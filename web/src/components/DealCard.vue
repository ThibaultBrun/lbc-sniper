<script setup lang="ts">
import { computed } from "vue";
import type { Ad } from "../supabase";

const props = defineProps<{ ad: Ad }>();

const score = computed(() => props.ad.deal_score ?? 0);

const scoreClass = computed(() => {
  if (score.value >= 80) return "border-emerald-500 bg-emerald-500/10";
  if (score.value >= 60) return "border-amber-500/60 bg-amber-500/5";
  if (score.value >= 40) return "border-slate-700 bg-slate-900/40";
  return "border-rose-900/40 bg-slate-900/30 opacity-70";
});

const scoreBadgeClass = computed(() => {
  if (score.value >= 80) return "bg-emerald-500 text-slate-950";
  if (score.value >= 60) return "bg-amber-500 text-slate-950";
  if (score.value >= 40) return "bg-slate-600 text-slate-100";
  return "bg-rose-900/60 text-rose-200";
});

const priceFmt = (v: number | null) =>
  v == null ? "?" : v.toLocaleString("fr-FR");

const discountPct = computed(() => {
  const market = props.ad.estimated_market_eur;
  const price = props.ad.current_price;
  if (!market || !price) return null;
  return ((market - price) / market) * 100;
});
</script>

<template>
  <a
    :href="ad.url"
    target="_blank"
    rel="noopener noreferrer"
    :class="[
      'group block rounded-xl border overflow-hidden transition hover:scale-[1.01] hover:shadow-xl hover:shadow-black/40',
      scoreClass,
    ]"
  >
    <div class="aspect-[4/3] w-full bg-slate-800 relative overflow-hidden">
      <img
        v-if="ad.image_url"
        :src="ad.image_url"
        :alt="ad.subject"
        class="h-full w-full object-cover transition group-hover:scale-105"
        loading="lazy"
      />
      <div
        v-else
        class="h-full w-full grid place-items-center text-slate-600 text-xs"
      >
        pas de photo
      </div>

      <div
        :class="[
          'absolute top-2 right-2 rounded-full px-2.5 py-1 text-xs font-bold tabular-nums',
          scoreBadgeClass,
        ]"
      >
        {{ score }}/100
      </div>

      <div
        v-if="ad.electric"
        class="absolute top-2 left-2 rounded bg-blue-500/90 text-white text-[10px] font-bold px-2 py-0.5 uppercase tracking-wider"
      >
        électrique
      </div>
    </div>

    <div class="p-3 space-y-2">
      <div class="flex items-baseline justify-between gap-2">
        <div class="text-lg font-bold tabular-nums">
          {{ priceFmt(ad.current_price) }} €
        </div>
        <div
          v-if="discountPct !== null"
          :class="[
            'text-xs font-semibold tabular-nums',
            discountPct >= 30
              ? 'text-emerald-400'
              : discountPct >= 0
                ? 'text-slate-400'
                : 'text-rose-400',
          ]"
        >
          marché ~{{ priceFmt(Math.round(ad.estimated_market_eur ?? 0)) }} €
          <span v-if="discountPct >= 0">(-{{ Math.round(discountPct) }}%)</span>
          <span v-else>(+{{ Math.round(-discountPct) }}%)</span>
        </div>
      </div>

      <div class="flex flex-wrap gap-1 text-[11px]">
        <span v-if="ad.brand" class="rounded bg-slate-800 px-2 py-0.5 text-slate-300">
          {{ ad.brand }}
        </span>
        <span v-if="ad.model" class="rounded bg-slate-800 px-2 py-0.5 text-slate-300">
          {{ ad.model }}
        </span>
        <span v-if="ad.year" class="rounded bg-slate-800 px-2 py-0.5 text-slate-300">
          {{ ad.year }}
        </span>
        <span v-if="ad.size_label" class="rounded bg-slate-800 px-2 py-0.5 text-slate-300">
          {{ ad.size_label }}
        </span>
        <span v-if="ad.wheel_size" class="rounded bg-slate-800 px-2 py-0.5 text-slate-300">
          {{ ad.wheel_size }}
        </span>
      </div>

      <h3 class="text-sm text-slate-200 line-clamp-2 min-h-[2.5rem]">
        {{ ad.subject }}
      </h3>

      <p
        v-if="ad.reasoning"
        class="text-xs text-slate-400 line-clamp-3 italic border-l-2 border-slate-700 pl-2"
      >
        {{ ad.reasoning }}
      </p>

      <div class="flex items-center justify-between text-xs text-slate-500 pt-1">
        <span>{{ ad.city ?? "?" }}</span>
        <span v-if="ad.condition_score !== null" class="tabular-nums">
          état {{ ad.condition_score }}/100
        </span>
      </div>
    </div>
  </a>
</template>
