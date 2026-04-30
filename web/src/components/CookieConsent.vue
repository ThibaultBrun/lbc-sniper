<script setup lang="ts">
import { useConsent } from "../consent";

const { consent, accept, reject } = useConsent();
</script>

<template>
  <Transition name="consent-slide">
    <div v-if="consent === 'unknown'" class="consent-banner" role="dialog" aria-labelledby="consent-title">
      <div class="max-w-5xl mx-auto px-4 sm:px-6 py-4 flex flex-col sm:flex-row items-start sm:items-center gap-3">
        <div class="flex-1 min-w-0">
          <p id="consent-title" class="font-semibold text-sm">🍪 On respecte ta vie privée</p>
          <p class="text-xs text-muted mt-1 leading-relaxed">
            On utilise quelques cookies pour mesurer l'audience du site (Google Analytics) et financer les analyses IA via la publicité (Google AdSense).
            <router-link to="/confidentialite" class="link-accent">En savoir plus</router-link>
          </p>
        </div>
        <div class="flex gap-2 shrink-0 w-full sm:w-auto">
          <button
            @click="reject"
            class="btn btn-ghost flex-1 sm:flex-none whitespace-nowrap"
            type="button"
          >
            Refuser
          </button>
          <button
            @click="accept"
            class="btn btn-primary flex-1 sm:flex-none whitespace-nowrap"
            type="button"
          >
            Accepter
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.consent-banner {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  z-index: 60;
  background-color: var(--color-bg-elevated);
  border-top: 1px solid var(--color-border);
  box-shadow: 0 -8px 24px rgb(15 23 42 / 0.08);
  color: var(--color-text);
}
[data-theme="dark"] .consent-banner {
  box-shadow: 0 -8px 24px rgb(0 0 0 / 0.3);
}
.consent-slide-enter-active,
.consent-slide-leave-active {
  transition: transform 0.3s ease, opacity 0.3s ease;
}
.consent-slide-enter-from,
.consent-slide-leave-to {
  transform: translateY(100%);
  opacity: 0;
}
</style>
