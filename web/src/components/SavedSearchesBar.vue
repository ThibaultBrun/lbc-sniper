<script setup lang="ts">
import { ref, computed } from "vue";
import { useAuth } from "../auth";
import { useSavedSearches, type SavedSearchFilters, type SavedSearch } from "../saved-searches";

const props = defineProps<{
  currentFilters: SavedSearchFilters;
}>();
const emit = defineEmits<{
  apply: [SavedSearchFilters];
}>();

const { isAuthenticated, signInWithGoogle } = useAuth();
const { searches, save, remove, update } = useSavedSearches();

const showSaveDialog = ref(false);
const showList = ref(false);
const newName = ref("");
const newNotifyMode = ref<"off" | "instant" | "daily">("daily");
const saving = ref(false);

const summary = computed(() => {
  const f = props.currentFilters;
  const parts: string[] = [];
  if (f.geo) parts.push(`📍 ${f.geo.label} (${f.radiusKm} km)`);
  if (f.categoryFilter) parts.push(f.categoryFilter);
  if (f.electricFilter !== "all")
    parts.push(f.electricFilter === "yes" ? "⚡ Électrique" : "Musculaire");
  if (f.priceMin !== null || f.priceMax !== null) {
    parts.push(`${f.priceMin ?? 0}-${f.priceMax ?? "∞"} €`);
  }
  if (f.searchText) parts.push(`"${f.searchText}"`);
  return parts.join(" • ") || "Aucun filtre";
});

async function handleSave() {
  if (!newName.value.trim()) return;
  saving.value = true;
  try {
    await save(newName.value.trim(), props.currentFilters, newNotifyMode.value);
    showSaveDialog.value = false;
    newName.value = "";
  } finally {
    saving.value = false;
  }
}

async function handleSaveClick() {
  if (!isAuthenticated.value) {
    await signInWithGoogle();
    return;
  }
  // Pre-rempli un nom suggere depuis le summary
  newName.value = summary.value.length > 50 ? summary.value.slice(0, 47) + "..." : summary.value;
  showSaveDialog.value = true;
}

function applySearch(s: SavedSearch) {
  emit("apply", s.filters);
  showList.value = false;
}

async function handleRemove(s: SavedSearch, e: MouseEvent) {
  e.stopPropagation();
  if (!confirm(`Supprimer "${s.name}" ?`)) return;
  await remove(s.id);
}

async function toggleNotifyMode(s: SavedSearch, e: MouseEvent) {
  e.stopPropagation();
  const next = s.notify_mode === "off" ? "daily" : "off";
  await update(s.id, { notify_mode: next });
}

function notifyLabel(mode: "off" | "instant" | "daily"): string {
  return mode === "off" ? "🔕" : mode === "instant" ? "🔔" : "📧";
}
</script>

<template>
  <div class="flex items-center gap-2">
    <!-- Mes recherches (dropdown) -->
    <div v-if="isAuthenticated && searches.length > 0" class="relative">
      <button
        @click="showList = !showList"
        class="flex items-center gap-1.5 rounded bg-slate-800 hover:bg-slate-700 px-3 py-1.5 text-sm text-slate-200 transition"
      >
        <span>⭐</span>
        <span>Mes recherches</span>
        <span class="text-xs text-slate-500">({{ searches.length }})</span>
      </button>
      <div
        v-if="showList"
        class="absolute right-0 top-full mt-1 w-80 max-h-96 overflow-y-auto bg-slate-900 border border-slate-700 rounded shadow-lg py-1 z-30"
      >
        <button
          v-for="s in searches"
          :key="s.id"
          @click="applySearch(s)"
          class="block w-full text-left px-3 py-2 hover:bg-slate-800 border-b border-slate-800/50 last:border-b-0"
        >
          <div class="flex items-center justify-between gap-2">
            <span class="text-sm text-slate-100 font-medium truncate">{{ s.name }}</span>
            <div class="flex items-center gap-1 shrink-0">
              <button
                @click="toggleNotifyMode(s, $event)"
                :title="s.notify_mode === 'off' ? 'Activer les alertes mail' : 'Désactiver les alertes'"
                class="text-base hover:scale-110 transition"
              >
                {{ notifyLabel(s.notify_mode) }}
              </button>
              <button
                @click="handleRemove(s, $event)"
                class="text-slate-500 hover:text-rose-400 transition px-1"
                title="Supprimer"
              >×</button>
            </div>
          </div>
        </button>
      </div>
      <div
        v-if="showList"
        class="fixed inset-0 z-20"
        @click="showList = false"
      ></div>
    </div>

    <!-- Bouton "Sauvegarder cette recherche" -->
    <button
      @click="handleSaveClick"
      class="flex items-center gap-1.5 rounded bg-emerald-600 hover:bg-emerald-500 px-3 py-1.5 text-sm font-medium text-slate-950 transition"
      title="Sauvegarder les filtres actuels en recherche favorite"
    >
      <span>⭐</span>
      <span>Sauvegarder</span>
    </button>

    <!-- Dialogue de sauvegarde -->
    <div
      v-if="showSaveDialog"
      class="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm grid place-items-center p-4"
      @click.self="showSaveDialog = false"
    >
      <div class="w-full max-w-md bg-slate-900 rounded-xl border border-slate-700 p-6 space-y-4">
        <h2 class="text-lg font-bold text-slate-100">Sauvegarder cette recherche</h2>

        <div class="text-xs text-slate-400 bg-slate-800/50 rounded p-2 leading-relaxed">
          <span class="font-semibold text-slate-300">Filtres :</span> {{ summary }}
        </div>

        <label class="block">
          <span class="text-sm text-slate-300">Nom</span>
          <input
            v-model="newName"
            type="text"
            placeholder="Ex: VTT enduro Bayonne 50km"
            class="mt-1 w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-slate-100 focus:border-emerald-500 focus:outline-none"
            @keydown.enter="handleSave"
          />
        </label>

        <label class="block">
          <span class="text-sm text-slate-300">Alerte mail</span>
          <select
            v-model="newNotifyMode"
            class="mt-1 w-full bg-slate-800 border border-slate-700 rounded px-3 py-2 text-slate-100"
          >
            <option value="off">Pas d'alerte</option>
            <option value="daily">Digest journalier</option>
            <option value="instant">À chaque nouvelle annonce</option>
          </select>
          <p class="mt-1 text-xs text-slate-500">
            On t'enverra un mail quand une nouvelle annonce correspond à cette recherche.
          </p>
        </label>

        <div class="flex justify-end gap-2 pt-2">
          <button
            @click="showSaveDialog = false"
            class="rounded bg-slate-800 hover:bg-slate-700 px-4 py-2 text-sm text-slate-200"
          >
            Annuler
          </button>
          <button
            @click="handleSave"
            :disabled="!newName.trim() || saving"
            class="rounded bg-emerald-500 hover:bg-emerald-400 disabled:opacity-50 px-4 py-2 text-sm font-bold text-slate-950"
          >
            {{ saving ? "..." : "Sauvegarder" }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
