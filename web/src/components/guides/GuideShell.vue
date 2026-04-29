<script setup lang="ts">
// Squelette commun a tous les guides : header, breadcrumb, footer, schema.org Article.
// Le contenu est passe via slot. Chaque guide injecte aussi son `title`,
// `description`, `slug` et `lastUpdate` pour le SEO + le breadcrumb.

import { onMounted, useSlots } from "vue";
import { useRouter } from "vue-router";

const props = defineProps<{
  title: string;
  description: string;
  slug: string;
  lastUpdate: string; // "30 avril 2026"
  readingMin: number; // estimation 200 mots/min
}>();

const router = useRouter();
const slots = useSlots();
void slots; // garde la ref pour eviter dead code

function goHome() {
  router.push({ name: "home" });
}

// SEO : on injecte les meta tags au montage. C'est best-effort cote SPA ;
// le prerender (script Node) regenere les meta proprement par URL pour
// que Google les voie au premier hit.
onMounted(() => {
  document.title = `${props.title} — Trouve Ton VTT`;
  const setMeta = (name: string, content: string, attr: "name" | "property" = "name") => {
    let m = document.querySelector(`meta[${attr}="${name}"]`);
    if (!m) {
      m = document.createElement("meta");
      m.setAttribute(attr, name);
      document.head.appendChild(m);
    }
    m.setAttribute("content", content);
  };
  setMeta("description", props.description);
  setMeta("og:title", props.title, "property");
  setMeta("og:description", props.description, "property");
  setMeta("og:url", `https://trouvetonvtt.fr/guides/${props.slug}`, "property");
  setMeta("og:type", "article", "property");
});
</script>

<template>
  <div class="min-h-screen flex flex-col">
    <header class="surface-header">
      <div class="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
        <button
          @click="goHome"
          class="text-xl font-bold tracking-tight hover:opacity-80 transition"
        >
          <span style="color: var(--color-accent-hover)">Trouve</span> Ton VTT
        </button>
        <router-link to="/guides" class="btn btn-ghost">← Tous les guides</router-link>
      </div>
    </header>

    <main class="max-w-3xl mx-auto px-6 py-10 w-full flex-1">
      <!-- Breadcrumb -->
      <nav class="text-xs text-subtle mb-6" aria-label="Breadcrumb">
        <router-link to="/" class="hover:opacity-80">Accueil</router-link>
        <span class="mx-1.5">›</span>
        <router-link to="/guides" class="hover:opacity-80">Guides</router-link>
        <span class="mx-1.5">›</span>
        <span>{{ title }}</span>
      </nav>

      <article class="space-y-6 leading-relaxed guide-prose">
        <header class="space-y-3 pb-6" style="border-bottom: 1px solid var(--color-border)">
          <h1 class="text-3xl font-bold text-strong">{{ title }}</h1>
          <p class="text-lg text-muted">{{ description }}</p>
          <div class="text-xs text-subtle flex items-center gap-3">
            <span>📅 {{ lastUpdate }}</span>
            <span>⏱ {{ readingMin }} min de lecture</span>
          </div>
        </header>

        <slot />

        <footer class="pt-8 mt-8" style="border-top: 1px solid var(--color-border)">
          <p class="text-sm text-muted">
            Tu cherches un VTT d'occasion ? <router-link to="/" class="link-accent font-medium">Vois les meilleures affaires du moment →</router-link>
          </p>
        </footer>
      </article>
    </main>

    <footer class="surface-footer">
      <div class="space-x-4">
        <router-link to="/guides" class="hover:opacity-80">Guides</router-link>
        <router-link to="/a-propos" class="hover:opacity-80">À propos</router-link>
        <router-link to="/mentions-legales" class="hover:opacity-80">Mentions légales</router-link>
      </div>
    </footer>
  </div>
</template>

<style scoped>
/* Typo des guides : titres + listes + paragraphes lisibles. */
.guide-prose :deep(h2) {
  @apply text-2xl font-bold mt-10 mb-3;
  color: var(--color-text-strong);
}
.guide-prose :deep(h3) {
  @apply text-xl font-semibold mt-6 mb-2;
  color: var(--color-text-strong);
}
.guide-prose :deep(p) {
  @apply text-base;
}
.guide-prose :deep(ul) {
  @apply list-disc ml-6 space-y-1.5 my-3;
}
.guide-prose :deep(ol) {
  @apply list-decimal ml-6 space-y-1.5 my-3;
}
.guide-prose :deep(strong) {
  color: var(--color-text-strong);
  font-weight: 600;
}
.guide-prose :deep(blockquote) {
  @apply pl-4 my-4 italic;
  border-left: 3px solid var(--color-accent);
  color: var(--color-text-muted);
}
.guide-prose :deep(.callout) {
  @apply rounded-lg p-4 my-4;
  background-color: var(--color-accent-soft);
  border: 1px solid var(--color-accent-soft-border);
}
.guide-prose :deep(.callout-warn) {
  @apply rounded-lg p-4 my-4;
  background-color: theme(colors.amber.50);
  border: 1px solid theme(colors.amber.200);
  color: theme(colors.amber.900);
}
[data-theme="dark"] .guide-prose :deep(.callout-warn) {
  background-color: theme(colors.amber.500 / 15%);
  border-color: theme(colors.amber.400 / 35%);
  color: theme(colors.amber.100);
}
</style>
