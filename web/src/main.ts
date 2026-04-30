import { createApp } from "vue";
import App from "./App.vue";
import { router } from "./router";
import "./style.css";
// Import theme.ts pour appliquer data-theme="..." des le boot (avant le premier render).
import "./theme";
// Side effect : applique le consent stocke (charge GA si accepte avant).
import "./consent";
import { trackPageView } from "./consent";

// Tracking GA4 : envoie un page_view au router Vue chaque fois qu'on change
// de route. Le 1er page_view (page d'arrivee) est envoye au moment ou GA se
// charge (apres consent), donc on skip ici si c'est la 1ere navigation.
let firstNav = true;
router.afterEach((to) => {
  if (firstNav) {
    firstNav = false;
    return;
  }
  trackPageView(to.fullPath);
});

createApp(App).use(router).mount("#app");
