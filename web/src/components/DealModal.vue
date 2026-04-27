<script setup lang="ts">
import { computed, onMounted, onUnmounted } from "vue";
import type { Ad } from "../supabase";

const props = defineProps<{ ad: Ad }>();
const emit = defineEmits<{ close: [] }>();

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

const headerBg = computed(() =>
  ({
    great: "bg-gradient-to-br from-emerald-600 to-emerald-500 text-slate-950",
    good: "bg-gradient-to-br from-emerald-700 to-emerald-600 text-slate-50",
    fair: "bg-gradient-to-br from-slate-700 to-slate-600 text-slate-100",
    poor: "bg-gradient-to-br from-amber-700 to-amber-600 text-slate-50",
    bad: "bg-gradient-to-br from-rose-900 to-rose-800 text-rose-100",
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

const onKey = (e: KeyboardEvent) => {
  if (e.key === "Escape") emit("close");
};

onMounted(() => {
  document.addEventListener("keydown", onKey);
  document.body.style.overflow = "hidden";
});
onUnmounted(() => {
  document.removeEventListener("keydown", onKey);
  document.body.style.overflow = "";
});
</script>

<template>
  <div
    class="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm grid place-items-center p-4 overflow-y-auto"
    @click.self="emit('close')"
  >
    <div
      class="relative w-full max-w-7xl bg-slate-900 rounded-2xl shadow-2xl shadow-black/60 border border-slate-700 overflow-hidden my-8"
      @click.stop
    >
      <!-- Bandeau verdict -->
      <div :class="['px-8 py-6 flex items-center justify-between gap-4', headerBg]">
        <div class="flex items-baseline gap-4">
          <span class="text-6xl font-black tabular-nums leading-none">{{ score }}</span>
          <div>
            <div class="text-2xl font-bold leading-tight">{{ tierLabel }}</div>
            <div class="text-xs uppercase tracking-widest opacity-75 mt-1">Analyse IA — Claude Opus</div>
          </div>
        </div>
        <button
          @click="emit('close')"
          class="rounded-full bg-black/20 hover:bg-black/40 w-10 h-10 grid place-items-center text-2xl leading-none transition shrink-0"
          aria-label="Fermer"
        >
          ×
        </button>
      </div>

      <div class="grid lg:grid-cols-[320px_1fr_1fr] gap-0">
        <!-- Colonne 1 : photo + prix + tags -->
        <div class="p-6 space-y-4 border-b lg:border-b-0 lg:border-r border-slate-800">
          <div class="aspect-square rounded-xl bg-slate-800 overflow-hidden">
            <img
              v-if="ad.image_url"
              :src="ad.image_url"
              :alt="ad.subject"
              class="h-full w-full object-cover"
            />
            <div v-else class="h-full w-full grid place-items-center text-slate-600">
              pas de photo
            </div>
          </div>

          <div class="space-y-2">
            <div class="text-4xl font-bold tabular-nums">
              {{ priceFmt(ad.current_price) }} €
            </div>
            <div v-if="ad.estimated_market_eur" class="text-sm">
              <span class="text-slate-400">Cote estimée</span>
              <span class="ml-2 tabular-nums font-semibold text-slate-200">
                {{ priceFmt(Math.round(ad.estimated_market_eur)) }} €
              </span>
              <span
                v-if="discountPct !== null"
                :class="[
                  'ml-2 text-base font-bold tabular-nums',
                  discountPct >= 30
                    ? 'text-emerald-400'
                    : discountPct >= 0
                      ? 'text-emerald-500'
                      : 'text-rose-400',
                ]"
              >
                <span v-if="discountPct >= 0">−{{ Math.round(discountPct) }}%</span>
                <span v-else>+{{ Math.round(-discountPct) }}%</span>
              </span>
            </div>
          </div>

          <div v-if="ad.brand || ad.model || ad.year" class="text-lg font-medium text-slate-100">
            {{ [ad.brand, ad.model, ad.year].filter(Boolean).join(" ") }}
          </div>

          <div class="flex flex-wrap gap-1.5 text-xs">
            <span v-if="ad.electric" class="rounded bg-blue-500 text-white font-bold px-2 py-1">
              ⚡ électrique
            </span>
            <span v-if="ad.size_label" class="rounded bg-slate-800 px-2 py-1 text-slate-300">
              taille {{ ad.size_label }}
            </span>
            <span v-if="ad.wheel_size" class="rounded bg-slate-800 px-2 py-1 text-slate-300">
              {{ ad.wheel_size }}
            </span>
            <span v-if="ad.frame_material" class="rounded bg-slate-800 px-2 py-1 text-slate-300">
              {{ ad.frame_material }}
            </span>
            <span
              v-if="ad.condition_score !== null"
              class="rounded bg-slate-800 px-2 py-1 text-slate-300 tabular-nums"
            >
              état {{ ad.condition_score }}/100
            </span>
          </div>

          <div class="text-sm text-slate-400 pt-2 border-t border-slate-800">
            <div class="font-medium text-slate-300">{{ ad.subject }}</div>
            <div class="text-xs mt-1">{{ ad.city ?? "?" }}</div>
          </div>

          <a
            :href="ad.url"
            target="_blank"
            rel="noopener noreferrer"
            class="block text-center px-4 py-3 rounded-lg font-bold uppercase tracking-wider text-sm bg-emerald-500 hover:bg-emerald-400 text-slate-950 transition"
          >
            Voir sur LeBonCoin →
          </a>
        </div>

        <!-- Colonne 2 : Analyse + description originale -->
        <div class="p-6 space-y-5 lg:max-h-[80vh] lg:overflow-y-auto border-b lg:border-b-0 lg:border-r border-slate-800">
          <section v-if="ad.reasoning">
            <h3 class="text-xs font-bold uppercase tracking-widest text-slate-400 mb-2 flex items-center gap-2">
              <span class="text-base">🧠</span> Analyse
            </h3>
            <p class="text-base text-slate-100 leading-relaxed">
              {{ ad.reasoning }}
            </p>
          </section>

          <section v-if="ad.body" class="pt-4 border-t border-slate-800/70">
            <h3 class="text-xs font-bold uppercase tracking-widest text-slate-500 mb-2">
              Description originale
            </h3>
            <p class="text-xs text-slate-400 leading-relaxed whitespace-pre-line">
              {{ ad.body }}
            </p>
          </section>
        </div>

        <!-- Colonne 3 : Pros / Cons -->
        <div class="p-6 space-y-5 lg:max-h-[80vh] lg:overflow-y-auto">
          <section v-if="ad.pros?.length">
            <h3 class="text-xs font-bold uppercase tracking-widest text-emerald-400 mb-3 flex items-center gap-2">
              <span class="text-lg">✓</span> Points forts
            </h3>
            <ul class="space-y-2">
              <li
                v-for="(p, i) in ad.pros"
                :key="`p${i}`"
                class="flex gap-3 text-sm text-emerald-50 bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-3 leading-relaxed"
              >
                <span class="text-emerald-400 font-bold shrink-0">✓</span>
                <span>{{ p }}</span>
              </li>
            </ul>
          </section>

          <section v-if="ad.cons?.length">
            <h3 class="text-xs font-bold uppercase tracking-widest text-amber-400 mb-3 flex items-center gap-2">
              <span class="text-lg">⚠</span> Points de vigilance
            </h3>
            <ul class="space-y-2">
              <li
                v-for="(c, i) in ad.cons"
                :key="`c${i}`"
                class="flex gap-3 text-sm text-amber-50 bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 leading-relaxed"
              >
                <span class="text-amber-400 font-bold shrink-0">⚠</span>
                <span>{{ c }}</span>
              </li>
            </ul>
          </section>
        </div>
      </div>
    </div>
  </div>
</template>
