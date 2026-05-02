<script setup lang="ts">
// Carte interactive de la zone couverte (200km autour de Bayonne).
// Utilise Leaflet + tuiles OpenStreetMap (gratuit, pas de cle API).
// Cropee sur la France via maxBounds + minZoom (pas de dezoom au-dela).

import { onMounted, onUnmounted, ref } from "vue";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const BAYONNE: [number, number] = [43.4933, -1.4747];
const RADIUS_KM = 200;

const mapEl = ref<HTMLDivElement | null>(null);
let map: L.Map | null = null;

onMounted(() => {
  if (!mapEl.value) return;

  // Bounds qui cropent sur la France metropolitaine (sans Espagne ni UK).
  // Sud-Ouest a peu pres a Andorre, Nord-Est a Strasbourg.
  const FRANCE_BOUNDS = L.latLngBounds(
    [42.3, -5.2],   // SW : sud des Landes / Hendaye
    [51.1, 8.3],    // NE : Strasbourg / Belgique
  );

  map = L.map(mapEl.value, {
    center: BAYONNE,
    zoom: 7,
    minZoom: 5,
    maxZoom: 10,
    maxBounds: FRANCE_BOUNDS,
    maxBoundsViscosity: 1.0,    // empeche de quitter les bounds
    zoomControl: true,
    scrollWheelZoom: false,     // evite de gener le scroll page
    attributionControl: true,
  });

  // Tuiles OpenStreetMap (libre, gratuit, pas de cle).
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "© OpenStreetMap",
    maxZoom: 19,
    bounds: FRANCE_BOUNDS,
  }).addTo(map);

  // Cercle de la zone couverte (200km).
  L.circle(BAYONNE, {
    radius: RADIUS_KM * 1000,
    color: "#10b981",
    weight: 2,
    fillColor: "#10b981",
    fillOpacity: 0.15,
  }).addTo(map);

  // Marker Bayonne au centre.
  L.circleMarker(BAYONNE, {
    radius: 6,
    color: "#10b981",
    weight: 3,
    fillColor: "white",
    fillOpacity: 1,
  })
    .addTo(map)
    .bindTooltip("Bayonne", { permanent: true, direction: "top", offset: [0, -8] });

  // Adapte le viewport pour bien voir le cercle des le mount.
  map.fitBounds(L.latLng(BAYONNE).toBounds(RADIUS_KM * 2 * 1000), {
    padding: [20, 20],
  });
});

onUnmounted(() => {
  if (map) {
    map.remove();
    map = null;
  }
});
</script>

<template>
  <div class="coverage-map-wrapper">
    <div ref="mapEl" class="coverage-map" aria-label="Carte de la zone couverte (200km autour de Bayonne)"></div>
    <p class="text-xs text-subtle mt-2 text-center">
      Zone couverte : 200 km autour de Bayonne
    </p>
  </div>
</template>

<style scoped>
.coverage-map-wrapper {
  width: 100%;
}
.coverage-map {
  width: 100%;
  height: 320px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  overflow: hidden;
  background-color: var(--color-bg-muted);
}
/* Override Leaflet default font (sans-serif systeme) */
.coverage-map :deep(.leaflet-container) {
  font-family: inherit;
  font-size: 12px;
  background: var(--color-bg-muted);
}
/* Tooltip Bayonne adapte au theme */
.coverage-map :deep(.leaflet-tooltip) {
  background: var(--color-bg-elevated);
  color: var(--color-text);
  border: 1px solid var(--color-border);
  box-shadow: var(--shadow-card);
  font-weight: 600;
}
.coverage-map :deep(.leaflet-tooltip-top:before) {
  border-top-color: var(--color-border);
}
</style>
