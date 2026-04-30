<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from "vue";
import type { Ad } from "../supabase";

const props = defineProps<{ ad: Ad }>();
const emit = defineEmits<{ close: [] }>();

const copied = ref(false);

// Mapping enum -> label visible (memes valeurs que dans App.vue / DealCard).
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

// Date de publication originale (champ first_publication renvoye par la
// plateforme d'origine). On affiche "il y a X jours" si recent, sinon date complete.
const publishedLabel = computed<string | null>(() => {
  const raw = (props.ad as Ad & { first_publication?: string | null }).first_publication;
  if (!raw) return null;
  const d = new Date(raw);
  if (isNaN(d.getTime())) return null;
  const now = Date.now();
  const ageMs = now - d.getTime();
  const oneDay = 86400 * 1000;
  if (ageMs < oneDay) {
    const hours = Math.floor(ageMs / 3600000);
    if (hours < 1) return "il y a moins d'une heure";
    return `il y a ${hours} h`;
  }
  const days = Math.floor(ageMs / oneDay);
  if (days < 30) return `il y a ${days} jour${days > 1 ? "s" : ""}`;
  return d.toLocaleDateString("fr-FR", { day: "2-digit", month: "long", year: "numeric" });
});

async function copyShareLink() {
  const url = `${globalThis.location.origin}/ad/${props.ad.id}`;
  try {
    await navigator.clipboard.writeText(url);
    copied.value = true;
    setTimeout(() => (copied.value = false), 2000);
  } catch {
    // Fallback: prompt user to copy manually
    globalThis.prompt("Copier le lien :", url);
  }
}

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

const headerTierClass = computed(() => `tier-${tier.value}`);

// Couleur de la jauge selon le tier (inline, meme logique que DealCard).
const TIER_COLORS: Record<string, string> = {
  great: "#10b981",
  good: "#059669",
  fair: "#94a3b8",
  poor: "#f59e0b",
  bad: "#f43f5e",
};
const gaugeColor = computed(() => TIER_COLORS[tier.value] ?? "#94a3b8");

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
  <div class="modal-backdrop-scroll" @click.self="emit('close')">
    <div class="modal-shell" @click.stop>
      <!-- Bandeau verdict : compacte sur mobile, etale sur desktop -->
      <div :class="['px-4 sm:px-8 py-4 sm:py-6 flex items-start justify-between gap-3', headerTierClass]">
        <div class="flex items-start gap-3 sm:gap-4 min-w-0 flex-1">
          <span class="text-4xl sm:text-6xl font-black tabular-nums leading-none shrink-0">{{ score }}</span>
          <div class="min-w-0 flex-1 pt-0.5 sm:pt-1">
            <div class="text-lg sm:text-2xl font-bold leading-tight truncate">{{ tierLabel }}</div>
            <div class="text-[10px] sm:text-xs uppercase tracking-widest opacity-75 mt-0.5 sm:mt-1">Analyse IA</div>
            <!-- Jauge 0-100 : couleur unique selon le tier (definie par .tier-* parent) -->
            <div class="score-gauge mt-2 sm:mt-2.5" role="progressbar" :aria-valuenow="score" aria-valuemin="0" aria-valuemax="100">
              <div class="score-gauge-fill" :style="{ width: `${score}%`, backgroundColor: gaugeColor }"></div>
            </div>
            <div class="text-[10px] opacity-75 mt-1 tabular-nums">{{ score }}/100</div>
          </div>
        </div>
        <div class="flex items-center gap-1.5 sm:gap-2 shrink-0">
          <button
            @click="copyShareLink"
            :class="['icon-btn-pill', copied ? 'icon-btn-pill-success' : '']"
            :aria-label="copied ? 'Lien copié' : 'Copier le lien partageable'"
          >
            <span v-if="copied" class="hidden sm:inline">✓ Copié</span>
            <span v-else class="hidden sm:inline">🔗 Partager</span>
            <span v-if="copied" class="sm:hidden">✓</span>
            <span v-else class="sm:hidden">🔗</span>
          </button>
          <button @click="emit('close')" class="icon-btn-circle" aria-label="Fermer">×</button>
        </div>
      </div>

      <div class="grid lg:grid-cols-[320px_1fr_1fr] gap-0">
        <!-- Colonne 1 (mobile : tout en haut) : photo + prix + CTA + tags + ville -->
        <div class="p-4 sm:p-6 space-y-3 sm:space-y-4 modal-col-divider">
          <a
            :href="ad.url"
            target="_blank"
            rel="noopener noreferrer"
            class="block aspect-[4/3] sm:aspect-square rounded-xl overflow-hidden group/img surface-muted"
            title="Ouvrir l'annonce d'origine"
          >
            <img
              v-if="ad.image_url"
              :src="ad.image_url"
              :alt="ad.subject"
              class="h-full w-full object-cover transition group-hover/img:scale-105"
              decoding="async"
              referrerpolicy="no-referrer"
              fetchpriority="high"
            />
            <div v-else class="h-full w-full grid place-items-center text-faint">
              pas de photo
            </div>
          </a>

          <!-- Prix + cote sur 1 ligne, plus compact mobile -->
          <div class="flex items-baseline justify-between gap-3">
            <div class="text-3xl sm:text-4xl font-bold tabular-nums leading-none">
              {{ priceFmt(ad.current_price) }} €
            </div>
            <div v-if="discountPct !== null" :class="[
              'text-lg font-bold tabular-nums',
              discountPct >= 30 ? 'text-emerald-500' : discountPct >= 0 ? 'text-emerald-600' : 'text-rose-500',
            ]">
              <span v-if="discountPct >= 0">−{{ Math.round(discountPct) }}%</span>
              <span v-else>+{{ Math.round(-discountPct) }}%</span>
            </div>
          </div>
          <div v-if="ad.estimated_market_eur" class="text-xs text-muted -mt-1">
            Cote estimée
            <span class="ml-1 tabular-nums font-semibold text-strong">
              {{ priceFmt(Math.round(ad.estimated_market_eur)) }} €
            </span>
          </div>

          <!-- CTA tres visible des le haut -->
          <a
            :href="ad.url"
            target="_blank"
            rel="noopener noreferrer"
            class="btn-cta block text-center w-full"
          >
            Voir l'annonce →
          </a>

          <div v-if="ad.brand || ad.model || ad.year" class="text-base sm:text-lg font-semibold pt-1">
            {{ [ad.brand, ad.model, ad.year].filter(Boolean).join(" ") }}
          </div>

          <div class="flex flex-wrap gap-1.5">
            <span v-if="vttCategoryLabel" class="tag-vtt-category">{{ vttCategoryLabel }}</span>
            <span v-if="ad.electric" class="tag-electric">⚡ électrique</span>
            <span v-if="ad.regyear" class="tag-strong tabular-nums">{{ ad.regyear }}</span>
            <span v-if="ad.mileage_km" class="tag-strong tabular-nums">
              {{ ad.mileage_km.toLocaleString("fr-FR") }} km
            </span>
            <span v-if="ad.size_label" class="tag">taille {{ ad.size_label }}</span>
            <span v-if="ad.wheel_size" class="tag">{{ ad.wheel_size }}</span>
            <span v-if="ad.frame_material" class="tag">{{ ad.frame_material }}</span>
            <span v-if="ad.fuel" class="tag">{{ ad.fuel }}</span>
            <span v-if="ad.gearbox" class="tag">{{ ad.gearbox }}</span>
          </div>

          <div class="text-xs text-muted flex flex-wrap gap-x-3 gap-y-0.5 pt-1">
            <span>📍 {{ ad.city ?? "?" }}</span>
            <span v-if="publishedLabel">📅 Publiée {{ publishedLabel }}</span>
          </div>
        </div>

        <!-- Colonne 2 : Pros + Cons en premier (info critique pour decision) -->
        <div class="p-4 sm:p-6 space-y-4 lg:max-h-[80vh] lg:overflow-y-auto modal-col-divider">
          <section v-if="ad.pros?.length">
            <h3 class="section-title section-title-pros flex items-center gap-2 mb-2">
              <span>✓</span> Points forts
            </h3>
            <ul class="space-y-1.5">
              <li v-for="(p, i) in ad.pros" :key="`p${i}`" class="flex gap-2 text-sm leading-snug">
                <span class="font-bold shrink-0" style="color: var(--color-accent)">✓</span>
                <span>{{ p }}</span>
              </li>
            </ul>
          </section>

          <section v-if="ad.cons?.length">
            <h3 class="section-title section-title-cons flex items-center gap-2 mb-2">
              <span>⚠</span> Points de vigilance
            </h3>
            <ul class="space-y-1.5">
              <li v-for="(c, i) in ad.cons" :key="`c${i}`" class="flex gap-2 text-sm leading-snug">
                <span class="font-bold shrink-0" style="color: var(--color-warning)">⚠</span>
                <span>{{ c }}</span>
              </li>
            </ul>
          </section>
        </div>

        <!-- Colonne 3 : Analyse longue + description originale (accordeon) -->
        <div class="p-4 sm:p-6 space-y-3 lg:max-h-[80vh] lg:overflow-y-auto">
          <section v-if="ad.reasoning">
            <h3 class="section-title flex items-center gap-2 mb-2">
              <span>🧠</span> Analyse IA
            </h3>
            <p class="text-sm leading-relaxed">{{ ad.reasoning }}</p>
          </section>

          <!-- Description originale : repliable, pas critique sur mobile -->
          <details v-if="ad.body" class="pt-3" style="border-top: 1px solid var(--color-border-subtle)">
            <summary class="section-title cursor-pointer hover:opacity-80 flex items-center gap-2 select-none">
              <span>📝</span> Description originale
              <span class="text-[10px] opacity-60 normal-case font-normal">(cliquer pour ouvrir)</span>
            </summary>
            <p class="text-xs leading-relaxed whitespace-pre-line text-muted mt-3">{{ ad.body }}</p>
          </details>

          <!-- Subject (titre LBC) en bas pour reference -->
          <div v-if="ad.subject" class="pt-3 text-xs text-subtle italic" style="border-top: 1px solid var(--color-border-subtle)">
            Titre original : « {{ ad.subject }} »
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
