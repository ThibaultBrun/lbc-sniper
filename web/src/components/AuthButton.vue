<script setup lang="ts">
import { ref } from "vue";
import { useAuth } from "../auth";
import { useTheme } from "../theme";

const { user, profile, isAuthenticated, isAdmin, signInWithGoogle, signOut } = useAuth();
const { theme } = useTheme();

const menuOpen = ref(false);
const signingIn = ref(false);

async function handleSignIn() {
  signingIn.value = true;
  try {
    await signInWithGoogle();
  } catch (e) {
    signingIn.value = false;
  }
}

async function handleSignOut() {
  menuOpen.value = false;
  await signOut();
}
</script>

<template>
  <div class="flex items-center gap-2">
    <!-- Theme toggle : visible meme sans compte -->
    <div class="theme-toggle" role="group" aria-label="Theme">
      <button
        @click="theme = 'light'"
        :class="['theme-toggle-btn', theme === 'light' ? 'theme-toggle-btn-active' : '']"
        title="Theme clair"
        aria-label="Theme clair"
      >☀</button>
      <button
        @click="theme = 'auto'"
        :class="['theme-toggle-btn', theme === 'auto' ? 'theme-toggle-btn-active' : '']"
        title="Auto (suit le systeme)"
        aria-label="Theme automatique"
      >◐</button>
      <button
        @click="theme = 'dark'"
        :class="['theme-toggle-btn', theme === 'dark' ? 'theme-toggle-btn-active' : '']"
        title="Theme sombre"
        aria-label="Theme sombre"
      >☾</button>
    </div>

  <div class="relative">
    <button
      v-if="!isAuthenticated"
      @click="handleSignIn"
      :disabled="signingIn"
      class="btn btn-ghost"
    >
      <svg viewBox="0 0 24 24" class="w-4 h-4" aria-hidden="true">
        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84A11 11 0 0 0 12 23z"/>
        <path fill="#FBBC05" d="M5.84 14.1c-.22-.66-.35-1.36-.35-2.1s.13-1.44.35-2.1V7.06H2.18A11 11 0 0 0 1 12c0 1.78.43 3.46 1.18 4.94l3.66-2.84z"/>
        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84C6.71 7.31 9.14 5.38 12 5.38z"/>
      </svg>
      <span>{{ signingIn ? "..." : "Se connecter" }}</span>
    </button>

    <button
      v-else
      @click="menuOpen = !menuOpen"
      class="btn btn-ghost"
    >
      <img
        v-if="profile?.avatar_url"
        :src="profile.avatar_url"
        :alt="profile?.display_name ?? ''"
        class="w-6 h-6 rounded-full"
        referrerpolicy="no-referrer"
      />
      <span class="hidden sm:inline max-w-[140px] truncate">
        {{ profile?.display_name ?? user?.email }}
      </span>
      <span v-if="isAdmin" class="badge-admin">Admin</span>
      <span class="text-subtle text-xs">▾</span>
    </button>

    <div
      v-if="menuOpen && isAuthenticated"
      class="dropdown-menu"
      @click.outside="menuOpen = false"
    >
      <div class="px-3 py-2 text-xs text-subtle" style="border-bottom: 1px solid var(--color-border)">
        Connecté en tant que<br>
        <span class="text-strong">{{ user?.email }}</span>
      </div>
      <router-link to="/favoris" @click="menuOpen = false" class="dropdown-item">
        ♥ Mes favoris
      </router-link>
      <router-link
        v-if="isAdmin"
        to="/admin/utilisateurs"
        @click="menuOpen = false"
        class="dropdown-item"
        style="border-top: 1px solid var(--color-border-subtle)"
      >
        👥 Utilisateurs (admin)
      </router-link>
      <button
        @click="handleSignOut"
        class="dropdown-item w-full text-left"
        style="border-top: 1px solid var(--color-border)"
      >
        Se déconnecter
      </button>
    </div>

    <!-- Backdrop pour fermer le menu en cliquant ailleurs -->
    <div
      v-if="menuOpen"
      class="fixed inset-0 z-20"
      @click="menuOpen = false"
    ></div>
  </div>
  </div>
</template>
