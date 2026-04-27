import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";

// L'app a un seul écran (la liste). Le router sert uniquement à gérer
// l'historique de l'URL pour permettre de partager le lien d'une analyse.
// App.vue lit `useRoute()` pour décider si la modale doit s'ouvrir.
const routes: RouteRecordRaw[] = [
  {
    path: "/",
    name: "home",
    // Composant placeholder rendu par <router-view>. App lit la route lui-même.
    component: { template: "<div></div>" },
  },
  {
    path: "/ad/:id(\\d+)",
    name: "ad",
    component: { template: "<div></div>" },
  },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
});
