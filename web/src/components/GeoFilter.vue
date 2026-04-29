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
  <div class="flex flex-wrap items-center gap-2 flex-1 min-w-[400px]">
    <span class="text-muted text-sm whitespace-nowrap">📍</span>

    <span v-if="modelValue" class="chip-accent">
      {{ modelValue.label }}
      <button @click="clearGeo" class="ml-1 font-bold" aria-label="Retirer la ville"
        style="color: var(--color-accent-hover)"
      >×</button>
    </span>

    <div v-else class="relative flex-1 min-w-[140px]">
      <input
        v-model="query"
        @focus="showSuggestions = true"
        @blur="delayedHide"
        type="text"
        placeholder="Commune (ex: Bayonne)"
        class="input-base w-full"
      />
      <div v-if="showSuggestions && suggestions.length > 0" class="dropdown-floating">
        <button
          v-for="c in suggestions"
          :key="c.insee"
          @mousedown.prevent="pickCommune(c)"
          class="dropdown-item w-full text-left"
        >
          {{ c.name }}
          <span class="text-xs text-subtle">({{ c.insee.substring(0, 2) }})</span>
        </button>
      </div>
    </div>

    <button
      v-if="!modelValue"
      @click="useMyPosition"
      :disabled="locating"
      class="btn btn-ghost whitespace-nowrap"
      :title="locationError ?? 'Utiliser ma position'"
    >
      📍 {{ locating ? "..." : "Ma position" }}
    </button>

    <!-- Jalons de rayon. Grise sans ville. -->
    <div class="flex items-center gap-1">
      <button
        v-for="km in [20, 50, 100, 200]"
        :key="km"
        type="button"
        @click="$emit('update:radiusKm', km)"
        :disabled="!modelValue"
        :class="modelValue && radiusKm === km ? 'chip-active' : 'chip-inactive'"
      >
        {{ km }} km
      </button>
    </div>

    <p v-if="locationError" class="basis-full text-xs" style="color: var(--color-danger-text)">{{ locationError }}</p>
  </div>
</template>
