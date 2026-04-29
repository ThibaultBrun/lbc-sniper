<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();

const page = computed(() => route.name as string);

function goHome() {
  router.push({ name: "home" });
}

const lastUpdate = "29 avril 2026";
</script>

<template>
  <div class="min-h-screen">
    <header class="border-b border-slate-800 bg-slate-900/40 backdrop-blur sticky top-0 z-10">
      <div class="max-w-3xl mx-auto px-6 py-4 flex items-center justify-between">
        <button
          @click="goHome"
          class="text-xl font-bold tracking-tight hover:opacity-80 transition"
        >
          <span class="text-emerald-400">Trouve</span> Ton VTT
        </button>
        <button
          @click="goHome"
          class="rounded bg-slate-800 hover:bg-slate-700 px-3 py-1 text-sm text-slate-200 transition"
        >
          ← Retour
        </button>
      </div>
    </header>

    <main class="max-w-3xl mx-auto px-6 py-10 prose prose-invert prose-slate">
      <!-- ================ A PROPOS ================ -->
      <article v-if="page === 'about'" class="text-slate-200 space-y-6 leading-relaxed">
        <h1 class="text-3xl font-bold text-slate-100">À propos</h1>

        <section>
          <p class="text-lg">
            <strong class="text-emerald-400">Trouve Ton VTT</strong> t'aide à dénicher les meilleures affaires VTT du moment, sans passer des heures à éplucher des centaines d'annonces.
          </p>
        </section>

        <section>
          <h2 class="text-xl font-bold text-slate-100 mt-6 mb-2">Ce qu'on fait</h2>
          <p>
            Plusieurs fois par jour, on consulte les nouvelles annonces VTT (enduro et descente) publiées sur Leboncoin. Pour chacune, une intelligence artificielle :
          </p>
          <ul class="list-disc ml-6 space-y-1.5">
            <li>identifie le modèle, l'année, les caractéristiques (suspension, taille, électrique ou non…)</li>
            <li>estime un prix de revente cohérent pour ce vélo précis sur le marché de l'occasion</li>
            <li>note l'annonce de 0 à 100 selon l'écart au prix marché — c'est ton <em>deal score</em></li>
            <li>liste les points forts et les points de vigilance à connaître avant de contacter le vendeur</li>
          </ul>
          <p>
            Tu vois immédiatement les vraies pépites surligner en vert, et tu peux filtrer par catégorie, électrique ou non, prix, et zone géographique (commune + rayon).
          </p>
        </section>

        <section>
          <h2 class="text-xl font-bold text-slate-100 mt-6 mb-2">Pour qui ?</h2>
          <p>
            Pour quiconque veut s'acheter un VTT d'occasion sans y passer ses soirées et sans se faire avoir sur le prix. Que tu cherches un enduro polyvalent, une bête de descente, une version électrique pour les longues sorties, ou une affaire collector, le service te remonte ce qui mérite ton attention.
          </p>
        </section>

        <section>
          <h2 class="text-xl font-bold text-slate-100 mt-6 mb-2">Important</h2>
          <p>
            Les analyses sont générées par une IA et fournies <strong>à titre indicatif</strong>. Elles peuvent se tromper, surtout sur des modèles rares ou des annonces peu détaillées. <strong>Vérifie toujours l'annonce originale, regarde les photos en grand, pose des questions au vendeur, et inspecte le vélo avant achat.</strong> On te donne une longueur d'avance, pas une garantie.
          </p>
          <p>
            Le service est <strong>gratuit</strong> et le restera. Trouve Ton VTT n'est ni partenaire, ni affilié à Leboncoin — c'est un projet indépendant qui s'appuie uniquement sur des annonces publiques.
          </p>
        </section>

        <section>
          <h2 class="text-xl font-bold text-slate-100 mt-6 mb-2">Une question, un retour ?</h2>
          <p>
            Écris-nous à <a href="mailto:contact@pista.bike" class="text-emerald-400 hover:underline">contact@pista.bike</a>. On lit tout, on répond quand on peut.
          </p>
        </section>
      </article>

      <!-- ================ MENTIONS LEGALES ================ -->
      <article v-else-if="page === 'legal'" class="text-slate-200 space-y-6 leading-relaxed">
        <h1 class="text-3xl font-bold text-slate-100">Mentions légales</h1>
        <p class="text-sm text-slate-500">Dernière mise à jour : {{ lastUpdate }}</p>

        <section>
          <h2 class="text-xl font-bold text-slate-100 mt-6 mb-2">Éditeur du site</h2>
          <p>
            Le site <strong>Trouve Ton VTT</strong> est édité par <strong>Shredlab</strong>.
          </p>
          <p>
            Contact : <a href="mailto:contact@pista.bike" class="text-emerald-400 hover:underline">contact@pista.bike</a>
          </p>
        </section>

        <section>
          <h2 class="text-xl font-bold text-slate-100 mt-6 mb-2">Hébergement</h2>
          <p>
            Le site est hébergé par <strong>Vercel Inc.</strong>, 340 S Lemon Ave #4133, Walnut, CA 91789, USA — <a href="https://vercel.com" class="text-emerald-400 hover:underline" target="_blank" rel="noopener">vercel.com</a>.
          </p>
          <p>
            La base de données est hébergée par <strong>Supabase Inc.</strong>, 970 Toa Payoh North #07-04, Singapore — <a href="https://supabase.com" class="text-emerald-400 hover:underline" target="_blank" rel="noopener">supabase.com</a>.
          </p>
        </section>

        <section>
          <h2 class="text-xl font-bold text-slate-100 mt-6 mb-2">Données affichées</h2>
          <p>
            Les annonces présentées sur ce site sont issues du site <strong>Leboncoin.fr</strong> et restent la propriété de leurs auteurs respectifs. Trouve Ton VTT n'est ni affilié, ni partenaire, ni sponsorisé par Leboncoin SA.
          </p>
          <p>
            Le service est fourni à titre gratuit et informatif. Trouve Ton VTT ne se porte pas garant de la véracité, de la disponibilité ou de l'état des biens présentés. Toute transaction se fait directement entre l'acheteur et le vendeur sur Leboncoin.
          </p>
        </section>

        <section>
          <h2 class="text-xl font-bold text-slate-100 mt-6 mb-2">Analyses générées par IA</h2>
          <p>
            Les scores, estimations de prix de marché, points forts et points de vigilance affichés sont générés automatiquement par un modèle d'intelligence artificielle (Claude, Anthropic). Ces analyses sont fournies à titre indicatif uniquement et peuvent contenir des erreurs ou approximations. Vérifiez toujours l'annonce originale et inspectez le bien avant tout achat.
          </p>
        </section>

        <section>
          <h2 class="text-xl font-bold text-slate-100 mt-6 mb-2">Propriété intellectuelle</h2>
          <p>
            La structure du site, son design, son code source sont la propriété de Shredlab. Les marques, modèles et photos des annonces appartiennent à leurs ayants droit respectifs.
          </p>
        </section>
      </article>

      <!-- ================ POLITIQUE DE CONFIDENTIALITE ================ -->
      <article v-else-if="page === 'privacy'" class="text-slate-200 space-y-6 leading-relaxed">
        <h1 class="text-3xl font-bold text-slate-100">Politique de confidentialité</h1>
        <p class="text-sm text-slate-500">Dernière mise à jour : {{ lastUpdate }}</p>

        <section>
          <h2 class="text-xl font-bold text-slate-100 mt-6 mb-2">Données personnelles collectées</h2>
          <p>
            Trouve Ton VTT <strong>ne demande aucune inscription</strong> et ne collecte aucune donnée personnelle de ses visiteurs. Pas de compte, pas de mot de passe, pas de profil.
          </p>
          <p>
            Si vous utilisez la fonction <em>« Ma position »</em>, votre navigateur vous demande l'autorisation. Les coordonnées GPS sont utilisées uniquement dans votre navigateur pour filtrer les annonces affichées — elles ne sont jamais envoyées à nos serveurs ni à des tiers.
          </p>
        </section>

        <section>
          <h2 class="text-xl font-bold text-slate-100 mt-6 mb-2">Cookies</h2>
          <p>
            Le site n'utilise aucun cookie de tracking ni d'analytics tiers (pas de Google Analytics, Facebook Pixel, etc.). L'hébergeur Vercel peut déposer un cookie technique nécessaire au fonctionnement du site (anti-DDoS).
          </p>
        </section>

        <section>
          <h2 class="text-xl font-bold text-slate-100 mt-6 mb-2">Données techniques (logs serveur)</h2>
          <p>
            Comme tout site web, l'hébergeur conserve des journaux d'accès anonymisés (adresse IP, navigateur, heure de visite) pendant une durée limitée à des fins de sécurité et de prévention des abus.
          </p>
        </section>

        <section>
          <h2 class="text-xl font-bold text-slate-100 mt-6 mb-2">Vos droits</h2>
          <p>
            Conformément au RGPD, vous disposez d'un droit d'accès, de rectification et d'opposition concernant vos données. Comme nous ne collectons pas de données personnelles identifiables, ces droits sont sans objet pour la consultation du site. Pour toute question : <a href="mailto:contact@pista.bike" class="text-emerald-400 hover:underline">contact@pista.bike</a>.
          </p>
        </section>
      </article>

      <!-- ================ CGU ================ -->
      <article v-else-if="page === 'tos'" class="text-slate-200 space-y-6 leading-relaxed">
        <h1 class="text-3xl font-bold text-slate-100">Conditions générales d'utilisation</h1>
        <p class="text-sm text-slate-500">Dernière mise à jour : {{ lastUpdate }}</p>

        <section>
          <h2 class="text-xl font-bold text-slate-100 mt-6 mb-2">1. Objet</h2>
          <p>
            Trouve Ton VTT est un service en ligne <strong>gratuit</strong> qui agrège des annonces VTT publiques issues de Leboncoin.fr et propose une analyse automatisée de leur intérêt grâce à un moteur d'intelligence artificielle.
          </p>
        </section>

        <section>
          <h2 class="text-xl font-bold text-slate-100 mt-6 mb-2">2. Accès au service</h2>
          <p>
            Le site est librement accessible, sans inscription. Shredlab se réserve le droit de modifier, suspendre ou interrompre le service à tout moment, sans préavis.
          </p>
        </section>

        <section>
          <h2 class="text-xl font-bold text-slate-100 mt-6 mb-2">3. Données présentées</h2>
          <p>
            Les annonces sont récupérées automatiquement depuis Leboncoin et peuvent être désactivées, modifiées ou périmées sans que cela soit reflété en temps réel sur Trouve Ton VTT. Les prix, descriptions et photos restent la propriété de leurs auteurs et de Leboncoin.
          </p>
        </section>

        <section>
          <h2 class="text-xl font-bold text-slate-100 mt-6 mb-2">4. Limites de responsabilité</h2>
          <p>
            Les analyses, scores et estimations affichés sont générés par une IA et fournis à titre <strong>purement indicatif</strong>. Shredlab ne garantit en aucune manière :
          </p>
          <ul class="list-disc ml-6 space-y-1">
            <li>la justesse des estimations de prix de marché</li>
            <li>la qualité, l'authenticité ou l'état réel des biens présentés</li>
            <li>la fiabilité des vendeurs</li>
            <li>la disponibilité continue du service</li>
          </ul>
          <p>
            <strong>Avant tout achat, vérifiez l'annonce originale, inspectez le bien et appliquez les précautions d'usage en cas de transaction entre particuliers.</strong> Shredlab ne saurait être tenu responsable d'un litige, d'une perte financière ou d'un préjudice consécutif à l'utilisation des informations affichées.
          </p>
        </section>

        <section>
          <h2 class="text-xl font-bold text-slate-100 mt-6 mb-2">5. Utilisation acceptable</h2>
          <p>
            L'utilisateur s'engage à ne pas perturber le fonctionnement du site (scraping massif, attaques, tentatives d'intrusion). Toute utilisation abusive pourra entraîner un blocage de l'accès.
          </p>
        </section>

        <section>
          <h2 class="text-xl font-bold text-slate-100 mt-6 mb-2">6. Droit applicable</h2>
          <p>
            Les présentes CGU sont régies par le droit français. Tout litige relèvera de la compétence des tribunaux français.
          </p>
        </section>
      </article>
    </main>

    <footer class="border-t border-slate-800 mt-12 py-6 text-center text-xs text-slate-500">
      <button @click="goHome" class="hover:text-slate-300">← Retour à l'accueil</button>
    </footer>
  </div>
</template>
