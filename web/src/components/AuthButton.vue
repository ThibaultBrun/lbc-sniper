<script setup lang="ts">
import { ref } from "vue";
import { useAuth } from "../auth";

const { user, profile, isAuthenticated, isAdmin, signInWithGoogle, signOut } = useAuth();

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
  <div class="relative">
    <button
      v-if="!isAuthenticated"
      @click="handleSignIn"
      :disabled="signingIn"
      class="flex items-center gap-2 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-50 px-3 py-1.5 text-sm text-slate-200 transition"
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
      class="flex items-center gap-2 rounded bg-slate-800 hover:bg-slate-700 px-2 py-1 text-sm text-slate-200 transition"
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
      <span
        v-if="isAdmin"
        class="text-[10px] font-bold uppercase tracking-wider bg-rose-500/20 border border-rose-500/40 text-rose-300 px-1.5 py-0.5 rounded"
      >Admin</span>
      <span class="text-slate-500 text-xs">▾</span>
    </button>

    <div
      v-if="menuOpen && isAuthenticated"
      class="absolute right-0 top-full mt-1 w-56 bg-slate-900 border border-slate-700 rounded shadow-lg py-1 z-30"
      @click.outside="menuOpen = false"
    >
      <div class="px-3 py-2 text-xs text-slate-500 border-b border-slate-800">
        Connecté en tant que<br>
        <span class="text-slate-200">{{ user?.email }}</span>
      </div>
      <router-link
        to="/favoris"
        @click="menuOpen = false"
        class="block px-3 py-2 text-sm text-slate-300 hover:bg-slate-800"
      >
        ♥ Mes favoris
      </router-link>
      <button
        @click="handleSignOut"
        class="w-full text-left px-3 py-2 text-sm text-slate-300 hover:bg-slate-800 border-t border-slate-800"
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
</template>
