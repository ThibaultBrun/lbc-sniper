import { createApp } from "vue";
import App from "./App.vue";
import { router } from "./router";
import "./style.css";
// Import theme.ts pour appliquer data-theme="..." des le boot (avant le premier render).
import "./theme";

createApp(App).use(router).mount("#app");
