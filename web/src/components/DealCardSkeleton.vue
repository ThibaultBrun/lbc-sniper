<script setup lang="ts">
// Skeleton card affiche pendant le chargement initial. Meme structure et
// proportions qu'une vraie DealCard pour eviter le shift visuel.
</script>

<template>
  <div class="card" aria-hidden="true">
    <!-- Header tier -->
    <div class="px-4 py-2.5 skeleton-shimmer" style="height: 38px"></div>
    <!-- Image -->
    <div class="aspect-[4/3] w-full skeleton-shimmer"></div>
    <!-- Infos -->
    <div class="p-3 space-y-2">
      <div class="h-5 w-24 rounded skeleton-shimmer"></div>
      <div class="h-4 w-3/4 rounded skeleton-shimmer"></div>
      <div class="flex gap-1.5">
        <div class="h-4 w-12 rounded skeleton-shimmer"></div>
        <div class="h-4 w-16 rounded skeleton-shimmer"></div>
      </div>
      <div class="h-3 w-full rounded skeleton-shimmer mt-2"></div>
      <div class="h-3 w-1/2 rounded skeleton-shimmer"></div>
    </div>
  </div>
</template>
