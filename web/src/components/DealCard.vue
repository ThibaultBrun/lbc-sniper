<script setup lang="ts">
import { computed, ref } from "vue";
import type { Ad } from "../supabase";

const props = defineProps<{ ad: Ad }>();

const expanded = ref(false);

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

const hasAnalysis = computed(
  () =>
    !!props.ad.reasoning ||
    (props.ad.pros && props.ad.pros.length > 0) ||
    (props.ad.cons && props.ad.cons.length > 0),
);
</script>

<template>
  <div
    :class="[
      'group block rounded-xl border overflow-hidden transition flex flex-col',
      scoreClass,
    ]"
  >
    <a
      :href="ad.url"
      target="_blank"
      rel="noopener noreferrer"
      class="block hover:opacity-95 transition"
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
            'absolute top-2 right-2 rounded-full px-2.5 py-1 text-xs font-bold tabular-nums shadow-lg',
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
    </a>

    <div class="p-3 space-y-2 flex-1 flex flex-col">
      <a :href="ad.url" target="_blank" rel="noopener noreferrer" class="space-y-2">
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

        <div class="flex items-center justify-between text-xs text-slate-500">
          <span>{{ ad.city ?? "?" }}</span>
          <span v-if="ad.condition_score !== null" class="tabular-nums">
            état {{ ad.condition_score }}/100
          </span>
        </div>
      </a>

      <!-- Bloc analyse IA expansible -->
      <div v-if="hasAnalysis" class="pt-2 border-t border-slate-800/80">
        <button
          @click="expanded = !expanded"
          class="text-xs font-semibold uppercase tracking-wider text-slate-400 hover:text-slate-200 flex items-center gap-1 transition"
        >
          <span>Analyse IA</span>
          <span class="text-slate-500">{{ expanded ? "▴" : "▾" }}</span>
        </button>

        <div v-if="expanded" class="mt-2 space-y-3 text-xs">
          <p
            v-if="ad.reasoning"
            class="text-slate-300 leading-relaxed border-l-2 border-slate-600 pl-2 italic"
          >
            {{ ad.reasoning }}
          </p>

          <div v-if="ad.pros && ad.pros.length > 0">
            <div class="text-emerald-400 font-semibold mb-1">✓ Points forts</div>
            <ul class="space-y-0.5 text-slate-300">
              <li v-for="(p, i) in ad.pros" :key="`p${i}`" class="flex gap-1.5">
                <span class="text-emerald-500/70 mt-0.5">·</span>
                <span>{{ p }}</span>
              </li>
            </ul>
          </div>

          <div v-if="ad.cons && ad.cons.length > 0">
            <div class="text-amber-400 font-semibold mb-1">⚠ Points de vigilance</div>
            <ul class="space-y-0.5 text-slate-300">
              <li v-for="(c, i) in ad.cons" :key="`c${i}`" class="flex gap-1.5">
                <span class="text-amber-500/70 mt-0.5">·</span>
                <span>{{ c }}</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
