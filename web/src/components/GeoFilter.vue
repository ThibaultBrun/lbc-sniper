<script setup lang="ts">
import { ref, watch } from "vue";
import { getCurrentPosition, searchCommunes, type Commune } from "../geo";

export type GeoFilterValue = {
  lat: number;
  lng: number;
  label: string; // "Bayonne (64)" ou "Ma position"
};

defineProps<{ modelValue: GeoFilterValue | null; radiusKm: number }>();
const emit = defineEmits<{
  "update:modelValue": [GeoFilterValue | null];
  "update:radiusKm": [number];
}>();

const query = ref("");
const suggestions = ref<Commune[]>([]);
const showSuggestions = ref(false);
const locating = ref(false);
const locationError = ref<string | null>(null);

let debounce: ReturnType<typeof setTimeout> | null = null;

watch(query, (q) => {
  if (debounce) clearTimeout(debounce);
  if (q.length < 2) {
    suggestions.value = [];
    return;
  }
  debounce = setTimeout(async () => {
    suggestions.value = await searchCommunes(q, 12);
  }, 80);
});

function pickCommune(c: Commune) {
  emit("update:modelValue", {
    lat: c.lat,
    lng: c.lng,
    label: `${c.name} (${c.insee.substring(0, 2)})`,
  });
  query.value = "";
  suggestions.value = [];
  showSuggestions.value = false;
}

async function useMyPosition() {
  locating.value = true;
  locationError.value = null;
  try {
    const pos = await getCurrentPosition();
    emit("update:modelValue", { ...pos, label: "Ma position" });
  } catch (e: any) {
    locationError.value = e?.message ?? "Geolocation refusee";
  } finally {
    locating.value = false;
  }
}

function clearGeo() {
  emit("update:modelValue", null);
  query.value = "";
}

function delayedHide() {
  setTimeout(() => {
    showSuggestions.value = false;
  }, 150);
}
</script>

<template>
  <div class="flex flex-col gap-2 flex-1 min-w-[280px]">
    <!-- Ligne 1 : ville + bouton ma position OU tag de la ville selectionnee -->
    <div class="flex items-center gap-2">
      <span class="text-slate-400 text-sm whitespace-nowrap">📍 Ville:</span>

      <span
        v-if="modelValue"
        class="rounded bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 px-2 py-1 text-sm flex items-center gap-1"
      >
        {{ modelValue.label }}
        <button
          @click="clearGeo"
          class="ml-1 text-emerald-400 hover:text-emerald-200 font-bold"
          aria-label="Retirer la ville"
        >×</button>
      </span>

      <div v-else class="relative flex-1">
        <input
          v-model="query"
          @focus="showSuggestions = true"
          @blur="delayedHide"
          type="text"
          placeholder="Tape une commune (ex: Bayonne)"
          class="w-full bg-slate-800 border border-slate-700 rounded px-3 py-1.5 text-slate-100 text-sm placeholder:text-slate-500 focus:border-emerald-500 focus:outline-none"
        />
        <div
          v-if="showSuggestions && suggestions.length > 0"
          class="absolute top-full left-0 right-0 mt-1 bg-slate-900 border border-slate-700 rounded shadow-lg max-h-72 overflow-y-auto z-20"
        >
          <button
            v-for="c in suggestions"
            :key="c.insee"
            @mousedown.prevent="pickCommune(c)"
            class="block w-full text-left px-3 py-1.5 text-sm hover:bg-slate-800 text-slate-200"
          >
            {{ c.name }}
            <span class="text-xs text-slate-500">({{ c.insee.substring(0, 2) }})</span>
          </button>
        </div>
      </div>

      <button
        v-if="!modelValue"
        @click="useMyPosition"
        :disabled="locating"
        class="rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-50 px-3 py-1.5 text-sm text-slate-200 whitespace-nowrap"
        :title="locationError ?? 'Utiliser ma position'"
      >
        📍 {{ locating ? "..." : "Ma position" }}
      </button>
    </div>

    <!-- Ligne 2 : slider de rayon (toujours visible, mais grise quand pas de ville) -->
    <div class="flex items-center gap-2">
      <span class="text-slate-400 text-sm whitespace-nowrap">Rayon:</span>
      <input
        type="range"
        min="5"
        max="500"
        step="5"
        :value="radiusKm"
        @input="$emit('update:radiusKm', Number(($event.target as HTMLInputElement).value))"
        :disabled="!modelValue"
        class="flex-1 accent-emerald-500 disabled:opacity-40"
      />
      <span
        :class="[
          'tabular-nums w-16 text-right text-sm',
          modelValue ? 'text-slate-200 font-semibold' : 'text-slate-500',
        ]"
      >
        {{ radiusKm }} km
      </span>
    </div>

    <p v-if="locationError" class="text-xs text-rose-400">{{ locationError }}</p>
  </div>
</template>
