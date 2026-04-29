<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { supabase } from "../supabase";
import { useAuth, type Profile } from "../auth";

const { isAdmin, loading: authLoading } = useAuth();
const router = useRouter();

const profiles = ref<Profile[]>([]);
const favoritesCount = ref<Record<string, number>>({});
const savedSearchesCount = ref<Record<string, number>>({});
const loading = ref(true);
const error = ref<string | null>(null);

async function load() {
  loading.value = true;
  error.value = null;
  try {
    // 3 requetes en parallele : profiles + counts par user.
    const [profRes, favRes, ssRes] = await Promise.all([
      supabase
        .from("profiles")
        .select("*")
        .order("created_at", { ascending: false }),
      supabase.from("favorites").select("user_id"),
      supabase.from("saved_searches").select("user_id"),
    ]);
    if (profRes.error) throw profRes.error;
    profiles.value = (profRes.data ?? []) as Profile[];
    // Compteurs par user_id (RLS limite ce que l'admin peut voir, mais
    // is_admin() bypass RLS sur profiles ; pour favorites/saved_searches
    // les policies actuelles n'autorisent que owner -> a creer si on veut
    // les vrais counts. En attendant on met 0 si rien retourne).
    const favBy: Record<string, number> = {};
    for (const f of (favRes.data ?? []) as { user_id: string }[]) {
      favBy[f.user_id] = (favBy[f.user_id] ?? 0) + 1;
    }
    favoritesCount.value = favBy;
    const ssBy: Record<string, number> = {};
    for (const s of (ssRes.data ?? []) as { user_id: string }[]) {
      ssBy[s.user_id] = (ssBy[s.user_id] ?? 0) + 1;
    }
    savedSearchesCount.value = ssBy;
  } catch (e: any) {
    error.value = e.message ?? String(e);
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  // Attendre que l'auth soit chargee, sinon isAdmin est false par defaut.
  while (authLoading.value) {
    await new Promise((r) => setTimeout(r, 50));
  }
  if (!isAdmin.value) {
    router.replace({ name: "home" });
    return;
  }
  load();
});

function fmtDate(s: string): string {
  return new Date(s).toLocaleString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
</script>

<template>
  <div class="min-h-screen flex flex-col">
    <header class="surface-header">
      <div class="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
        <h1 class="text-xl font-bold tracking-tight">
          <router-link to="/" class="hover:opacity-80">
            <span style="color: var(--color-accent-hover)">Trouve</span> Ton VTT
          </router-link>
          <span class="ml-2 text-sm font-normal text-muted">— Admin / Utilisateurs</span>
        </h1>
        <router-link to="/" class="btn btn-ghost">← Retour</router-link>
      </div>
    </header>

    <main class="max-w-5xl mx-auto px-6 py-8 w-full flex-1">
      <div v-if="loading" class="text-center text-subtle py-12">Chargement…</div>

      <div v-else-if="error" class="panel-error">
        <p class="font-semibold">Erreur</p>
        <p class="text-sm mt-1">{{ error }}</p>
      </div>

      <div v-else>
        <p class="text-sm text-muted mb-4">
          {{ profiles.length }} utilisateur{{ profiles.length > 1 ? "s" : "" }} inscrit{{ profiles.length > 1 ? "s" : "" }}
        </p>

        <div class="surface-elevated rounded-xl overflow-hidden">
          <table class="w-full text-sm">
            <thead>
              <tr class="text-left text-xs uppercase tracking-wider text-muted" style="border-bottom: 1px solid var(--color-border)">
                <th class="px-4 py-3">Utilisateur</th>
                <th class="px-4 py-3">Email</th>
                <th class="px-4 py-3 text-right tabular-nums">Favoris</th>
                <th class="px-4 py-3 text-right tabular-nums">Recherches</th>
                <th class="px-4 py-3">Role</th>
                <th class="px-4 py-3">Inscrit le</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="p in profiles"
                :key="p.id"
                style="border-top: 1px solid var(--color-border-subtle)"
              >
                <td class="px-4 py-3">
                  <div class="flex items-center gap-2">
                    <img
                      v-if="p.avatar_url"
                      :src="p.avatar_url"
                      :alt="p.display_name ?? ''"
                      class="w-6 h-6 rounded-full"
                      referrerpolicy="no-referrer"
                    />
                    <span class="font-medium">{{ p.display_name ?? "—" }}</span>
                  </div>
                </td>
                <td class="px-4 py-3 text-muted">{{ p.email ?? "—" }}</td>
                <td class="px-4 py-3 text-right tabular-nums">
                  {{ favoritesCount[p.id] ?? 0 }}
                </td>
                <td class="px-4 py-3 text-right tabular-nums">
                  {{ savedSearchesCount[p.id] ?? 0 }}
                </td>
                <td class="px-4 py-3">
                  <span v-if="p.role === 'admin'" class="badge-admin">Admin</span>
                  <span v-else class="text-subtle">user</span>
                </td>
                <td class="px-4 py-3 text-subtle text-xs tabular-nums">
                  {{ fmtDate(p.created_at) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </main>
  </div>
</template>
