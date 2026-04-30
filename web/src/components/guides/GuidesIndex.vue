<script setup lang="ts">
// Page index qui liste tous les guides editoriaux. Sert de hub SEO et
// d'entree pour les utilisateurs en phase de recherche d'information.
import { onMounted } from "vue";
import { useRouter } from "vue-router";

const router = useRouter();

function goHome() {
  router.push({ name: "home" });
}

const guides = [
  {
    slug: "comment-choisir-vtt-occasion",
    title: "Comment choisir un VTT d'occasion en 2026",
    description: "Guide complet pour acheter un VTT enduro, descente ou all-mountain d'occasion sans se faire avoir.",
    readingMin: 8,
    icon: "🛒",
    tag: "Achat",
  },
  {
    slug: "enduro-vs-dh-vs-all-mountain",
    title: "VTT enduro, DH, all-mountain : quelle catégorie pour quel usage ?",
    description: "Comprendre les différences entre les catégories pour choisir selon ton terrain et ta façon de rouler.",
    readingMin: 6,
    icon: "🚵",
    tag: "Catégories",
  },
  {
    slug: "decrypter-annonce-leboncoin",
    title: "Décrypter une annonce VTT entre particuliers",
    description: "Reconnaître les annonces honnêtes, les arnaques et les vélos volés. Questions à poser, signaux d'alerte.",
    readingMin: 7,
    icon: "🕵",
    tag: "Sécurité",
  },
];

onMounted(() => {
  document.title = "Guides VTT — Trouve Ton VTT";
  const setMeta = (name: string, content: string, attr: "name" | "property" = "name") => {
    let m = document.querySelector(`meta[${attr}="${name}"]`);
    if (!m) {
      m = document.createElement("meta");
      m.setAttribute(attr, name);
      document.head.appendChild(m);
    }
    m.setAttribute("content", content);
  };
  setMeta("description", "Guides pratiques pour choisir et acheter un VTT d'occasion : comparatifs, checklists, conseils anti-arnaque.");
});
</script>

<template>
  <div class="min-h-screen flex flex-col">
    <header class="surface-header">
      <div class="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
        <button
          @click="goHome"
          class="text-xl font-bold tracking-tight hover:opacity-80 transition"
        >
          <span style="color: var(--color-accent-hover)">Trouve</span> Ton VTT
        </button>
        <button @click="goHome" class="btn btn-ghost">← Retour aux annonces</button>
      </div>
    </header>

    <main class="max-w-4xl mx-auto px-6 py-10 w-full flex-1">
      <header class="space-y-3 mb-10">
        <h1 class="text-4xl font-bold text-strong">Guides VTT</h1>
        <p class="text-lg text-muted max-w-2xl">
          Avant d'acheter, lis. On a écrit ces guides pour t'éviter les pièges classiques de l'occasion VTT et
          t'aider à reconnaître une vraie bonne affaire.
        </p>
      </header>

      <div class="grid gap-4 sm:grid-cols-2">
        <router-link
          v-for="g in guides"
          :key="g.slug"
          :to="`/guides/${g.slug}`"
          class="card card-hover p-5 flex flex-col gap-3"
        >
          <div class="flex items-center gap-2">
            <span class="text-2xl">{{ g.icon }}</span>
            <span class="text-xs font-bold uppercase tracking-wider" style="color: var(--color-accent-hover)">
              {{ g.tag }}
            </span>
          </div>
          <h2 class="text-lg font-bold leading-tight text-strong">{{ g.title }}</h2>
          <p class="text-sm text-muted leading-relaxed flex-1">{{ g.description }}</p>
          <div class="flex items-center justify-between text-xs text-subtle pt-2">
            <span>⏱ {{ g.readingMin }} min</span>
            <span class="font-semibold" style="color: var(--color-accent-hover)">Lire →</span>
          </div>
        </router-link>
      </div>

      <div class="mt-12 panel-pros">
        <h3 class="font-bold text-base mb-2">Tu veux qu'on couvre un sujet en particulier ?</h3>
        <p class="text-sm">
          Écris-nous à <a href="mailto:contact@trouvetonvtt.fr" class="link-accent font-medium">contact@trouvetonvtt.fr</a>
          — on lit tout, on rédige les guides en fonction des questions qui reviennent.
        </p>
      </div>
    </main>

    <footer class="surface-footer">
      <div class="space-x-4">
        <router-link to="/a-propos" class="hover:opacity-80">À propos</router-link>
        <router-link to="/mentions-legales" class="hover:opacity-80">Mentions légales</router-link>
        <router-link to="/confidentialite" class="hover:opacity-80">Confidentialité</router-link>
        <router-link to="/cgu" class="hover:opacity-80">CGU</router-link>
      </div>
    </footer>
  </div>
</template>
