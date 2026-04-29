import { createRouter, createWebHistory, type RouteRecordRaw } from "vue-router";

// L'app a un seul ecran (la liste). Le router sert uniquement a gerer
// l'historique de l'URL pour permettre de partager le lien d'une analyse,
// et a basculer entre la home publique (VTT seulement) et /secret (tout).
const placeholder = { template: "<div></div>" };

const routes: RouteRecordRaw[] = [
  { path: "/", name: "home", component: placeholder },
  // /secret : meme UI que /, mais affiche toutes les categories
  { path: "/secret", name: "secret", component: placeholder },
  // Modale d'annonce, ouvrable depuis n'importe quelle vue
  { path: "/ad/:id(\\d+)", name: "ad", component: placeholder },
  { path: "/secret/ad/:id(\\d+)", name: "secret-ad", component: placeholder },
  // Page favoris (auth required cote app, pas cote routing)
  { path: "/favoris", name: "favorites", component: placeholder },
  // Pages statiques
  { path: "/a-propos", name: "about", component: placeholder },
  { path: "/mentions-legales", name: "legal", component: placeholder },
  { path: "/confidentialite", name: "privacy", component: placeholder },
  { path: "/cgu", name: "tos", component: placeholder },
  // Admin (visible uniquement aux users avec role='admin', controle cote AdminUsers.vue)
  { path: "/admin/utilisateurs", name: "admin-users", component: placeholder },
];

export const router = createRouter({
  history: createWebHistory(),
  routes,
});
