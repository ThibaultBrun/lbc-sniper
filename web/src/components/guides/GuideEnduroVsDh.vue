<script setup lang="ts">
import GuideShell from "./GuideShell.vue";
</script>

<template>
  <GuideShell
    title="VTT enduro, DH, all-mountain : quelle catégorie pour quel usage ?"
    description="Comprendre les différences entre VTT enduro, DH, all-mountain, trail et XC pour choisir la bonne catégorie selon ton terrain et ta façon de rouler."
    slug="enduro-vs-dh-vs-all-mountain"
    last-update="30 avril 2026"
    :reading-min="6"
  >
    <p>
      Quand tu débarques sur Le Bon Coin et que tu vois "VTT enduro", "VTT all-mountain", "VTT DH" et "VTT XC",
      tu te dis que ces gens parlent une langue étrangère. Voici les vraies différences, expliquées par
      l'usage — pas par le marketing.
    </p>

    <h2>Le débattement, premier critère</h2>
    <p>
      Le <strong>débattement</strong>, c'est la distance que la suspension peut absorber. Plus il est grand, plus
      le vélo peut encaisser de gros chocs, mais plus il est lourd et moins il pédale facilement à la montée.
    </p>

    <table style="width:100%; margin: 1rem 0; border-collapse: collapse">
      <thead>
        <tr style="border-bottom: 2px solid var(--color-border-strong); text-align: left">
          <th style="padding: 0.5rem">Catégorie</th>
          <th style="padding: 0.5rem">Débattement</th>
          <th style="padding: 0.5rem">Poids</th>
          <th style="padding: 0.5rem">Angle direction</th>
        </tr>
      </thead>
      <tbody>
        <tr style="border-bottom: 1px solid var(--color-border-subtle)">
          <td style="padding: 0.5rem">XC / cross-country</td>
          <td style="padding: 0.5rem">100-120 mm</td>
          <td style="padding: 0.5rem">10-12 kg</td>
          <td style="padding: 0.5rem">67-69°</td>
        </tr>
        <tr style="border-bottom: 1px solid var(--color-border-subtle)">
          <td style="padding: 0.5rem">Trail / down-country</td>
          <td style="padding: 0.5rem">120-140 mm</td>
          <td style="padding: 0.5rem">12-14 kg</td>
          <td style="padding: 0.5rem">66-67°</td>
        </tr>
        <tr style="border-bottom: 1px solid var(--color-border-subtle)">
          <td style="padding: 0.5rem">All-mountain</td>
          <td style="padding: 0.5rem">140-150 mm</td>
          <td style="padding: 0.5rem">13-14 kg</td>
          <td style="padding: 0.5rem">65-66°</td>
        </tr>
        <tr style="border-bottom: 1px solid var(--color-border-subtle)">
          <td style="padding: 0.5rem">Enduro</td>
          <td style="padding: 0.5rem">150-170 mm</td>
          <td style="padding: 0.5rem">14-15 kg</td>
          <td style="padding: 0.5rem">63-65°</td>
        </tr>
        <tr>
          <td style="padding: 0.5rem">DH / freeride</td>
          <td style="padding: 0.5rem">180-200 mm</td>
          <td style="padding: 0.5rem">15-17 kg</td>
          <td style="padding: 0.5rem">62-64°</td>
        </tr>
      </tbody>
    </table>

    <h2>XC (cross-country) — efficacité avant tout</h2>
    <p>
      Le XC, c'est <strong>le marathon du VTT</strong>. Vélos légers, suspension limitée, géométrie agressive
      pour pédaler vite. Tu vas l'aimer si :
    </p>
    <ul>
      <li>Tu fais des sorties longues (40+ km) sur sentiers roulants</li>
      <li>Tu cours en compétition ou tu veux du chrono</li>
      <li>Ton terrain c'est plutôt collines forestières, pas la montagne</li>
    </ul>
    <p>
      <strong>Inadapté pour</strong> : les bike-parks, les descentes techniques, les sentiers caillouteux exigeants.
    </p>

    <h2>Trail / down-country — le polyvalent moderne</h2>
    <p>
      Catégorie hybride née ces dernières années. Plus de suspension qu'un XC, géométrie plus relax, mais
      ça reste léger et ça pédale bien. Tu vas l'aimer si :
    </p>
    <ul>
      <li>Tu veux UN seul vélo pour tout faire (rando + descente technique modérée)</li>
      <li>Ton kilométrage hebdo est élevé mais tu aimes les descentes joueuses</li>
      <li>Tu n'es pas un destructeur de matos</li>
    </ul>

    <h2>All-mountain — le couteau suisse</h2>
    <p>
      LE meilleur compromis pour 80% des riders qui ne savent pas quoi choisir. Avec 140-150 mm, tu pédales
      raisonnablement à la montée et tu peux tout descendre sauf de la DH pure. C'est notre catégorie préférée
      pour <strong>un vélo unique</strong>.
    </p>
    <ul>
      <li>Tu enchaînes montée + descente sur des sentiers de montagne (Pyrénées, Alpes, Massif Central)</li>
      <li>Tu fais 1 ou 2 sorties bike-park par an, sans plus</li>
      <li>Tu cherches polyvalence > spécialisation</li>
    </ul>
    <p>
      <strong>Modèles repères</strong> : Specialized Stumpjumper, Trek Fuel EX, Lapierre Zesty, Cube Stereo,
      Norco Sight.
    </p>

    <h2>Enduro — pour envoyer fort</h2>
    <p>
      Aujourd'hui, "enduro" c'est devenu LA catégorie reine du VTT moderne. Suspension généreuse (160-170 mm),
      géo très inclinée pour la stabilité à haute vitesse, mais ça pédale toujours (contrairement au DH).
      Tu vas l'aimer si :
    </p>
    <ul>
      <li>Tu cherches l'adrénaline en descente, sur du terrain caillouteux et pentu</li>
      <li>Tu acceptes d'être moins à l'aise dans les longues montées</li>
      <li>Tu fais beaucoup de bike-park ou tu vis dans une région montagneuse</li>
    </ul>
    <p>
      <strong>Modèles repères</strong> : Commencal Meta TR/AM, Nukeproof Mega, Santa Cruz Megatower, YT Capra,
      Specialized Enduro.
    </p>

    <div class="callout">
      <strong>Notre conseil :</strong> en enduro moderne, le poids ne joue plus comme avant. Un Commencal Meta
      à 15 kg te fera des montées tranquilles si tu acceptes d'y aller à 8-10 km/h. C'est une question de mental.
    </div>

    <h2>DH / descente — réservé aux puristes</h2>
    <p>
      Le VTT DH, c'est <strong>un vélo qui ne pédale pas</strong>. 200 mm de débattement, double suspension,
      angle de direction très ouvert (62-63°). Conçu uniquement pour descendre des pistes de bike-park ou de
      coupe du monde. Tu vas l'aimer si :
    </p>
    <ul>
      <li>Tu fais exclusivement de la descente, en remontée mécanique ou navette</li>
      <li>Tu cherches le maximum de stabilité et de tolérance aux erreurs en descente engagée</li>
      <li>Tu ne comptes pas pédaler une montée de ta vie</li>
    </ul>
    <p>
      <strong>Modèles repères</strong> : Commencal Supreme, Canyon Sender, Santa Cruz V10, YT Tues.
    </p>

    <div class="callout-warn">
      <strong>⚠️ Achat occasion :</strong> les VTT DH ont souvent été utilisés en compétition ou bike-park
      intensif. Vérifie particulièrement les pivots de suspension, les soudures, et l'état général du cadre.
      Un cadre fissuré sur un DH = poubelle.
    </div>

    <h2>Et le VTT freeride ?</h2>
    <p>
      Le freeride, c'est un peu un dinosaure. Entre l'enduro et le DH, conçu pour les "big mountain" et les
      gros drops. Aujourd'hui le marché s'est concentré sur enduro/DH, et ces vélos sont rares. Si tu en vois
      un, c'est souvent du Commencal Furious ou du Bombtrack, et c'est plutôt orienté tricks et freeride pur.
    </p>

    <h2>Et l'électrique dans tout ça ?</h2>
    <p>
      L'électrique (VAE / e-MTB) suit la même logique de catégories : tu trouves du e-trail, du e-all-mountain,
      du e-enduro. Le moteur ajoute 5-7 kg, mais te permet de faire 2-3x plus de descentes par sortie. Si tu
      hésites entre musculaire et VAE pour ton premier VTT moderne, voici la règle simple :
    </p>
    <ul>
      <li><strong>Musculaire si</strong> : tu aimes le challenge à la montée, tu fais surtout des sorties courtes (1-2h), tu as moins de 35-40 ans en bonne forme.</li>
      <li><strong>Électrique si</strong> : tu veux maximiser les descentes, tu as une condition physique limitée, tu fais des sorties longues type "tour montagne".</li>
    </ul>

    <h2>En résumé : 3 conseils</h2>
    <ol>
      <li><strong>Si tu débutes ou veux un seul vélo :</strong> all-mountain. Tu pourras tout faire pendant 5 ans.</li>
      <li><strong>Si tu sais déjà que tu veux envoyer :</strong> enduro. C'est l'investissement long terme le plus pertinent.</li>
      <li><strong>Évite le DH</strong> sauf si tu as déjà un autre vélo pour la rando, et que tu as accès à des remontées mécaniques régulièrement.</li>
    </ol>
  </GuideShell>
</template>
