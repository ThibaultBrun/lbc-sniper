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

function asArrayFilter(value: string | string[] | null | undefined): string[] {
  if (Array.isArray(value)) return value.filter(Boolean);
  return value ? [value] : [];
}

const summary = computed(() => {
  const f = props.currentFilters;
  const parts: string[] = [];
  if (f.geo) parts.push(`📍 ${f.geo.label} (${f.radiusKm} km)`);
  if (f.categoryFilter) parts.push(f.categoryFilter);
  const types = asArrayFilter(f.vttCategoryFilter);
  if (types.length) parts.push(`Type: ${types.join(", ")}`);
  const sizes = asArrayFilter(f.sizeFilter);
  if (sizes.length) parts.push(`Taille: ${sizes.join(", ")}`);
  const wheels = asArrayFilter(f.wheelFilter);
  if (wheels.length) parts.push(`Roues: ${wheels.join(", ")}`);
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
      <button @click="showList = !showList" class="btn btn-ghost">
        <span>⭐</span>
        <span>Mes recherches</span>
        <span class="text-xs text-subtle">({{ searches.length }})</span>
      </button>
      <div v-if="showList" class="dropdown-menu w-80 max-h-96 overflow-y-auto">
        <button
          v-for="s in searches"
          :key="s.id"
          @click="applySearch(s)"
          class="dropdown-item w-full text-left"
          style="border-bottom: 1px solid var(--color-border-subtle)"
        >
          <div class="flex items-center justify-between gap-2">
            <span class="text-sm font-medium truncate">{{ s.name }}</span>
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
                class="text-subtle hover:text-rose-400 transition px-1"
                title="Supprimer"
              >×</button>
            </div>
          </div>
        </button>
      </div>
      <div v-if="showList" class="fixed inset-0 z-20" @click="showList = false"></div>
    </div>

    <!-- Bouton "Sauvegarder cette recherche" -->
    <button @click="handleSaveClick" class="btn btn-primary"
      title="Sauvegarder les filtres actuels en recherche favorite"
    >
      <span>⭐</span>
      <span>Sauvegarder</span>
    </button>

    <!-- Dialogue de sauvegarde -->
    <div v-if="showSaveDialog" class="modal-backdrop" @click.self="showSaveDialog = false">
      <div class="modal-shell-sm">
        <h2 class="text-lg font-bold">Sauvegarder cette recherche</h2>

        <div class="text-xs text-muted rounded p-2 leading-relaxed surface-muted">
          <span class="font-semibold text-strong">Filtres :</span> {{ summary }}
        </div>

        <label class="block">
          <span class="text-sm">Nom</span>
          <input
            v-model="newName"
            type="text"
            placeholder="Ex: VTT enduro Bayonne 50km"
            class="input-base mt-1 w-full py-2"
            @keydown.enter="handleSave"
          />
        </label>

        <label class="block">
          <span class="text-sm">Alerte mail</span>
          <select v-model="newNotifyMode" class="input-base mt-1 w-full py-2">
            <option value="off">Pas d'alerte</option>
            <option value="daily">Digest journalier</option>
            <option value="instant">À chaque nouvelle annonce</option>
          </select>
          <p class="mt-1 text-xs text-subtle">
            On t'enverra un mail quand une nouvelle annonce correspond à cette recherche.
          </p>
        </label>

        <div class="flex justify-end gap-2 pt-2">
          <button @click="showSaveDialog = false" class="btn btn-ghost px-4 py-2">
            Annuler
          </button>
          <button @click="handleSave" :disabled="!newName.trim() || saving" class="btn btn-primary px-4 py-2 font-bold">
            {{ saving ? "..." : "Sauvegarder" }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
