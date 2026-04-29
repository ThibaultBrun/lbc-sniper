<script setup lang="ts">
import GuideShell from "./GuideShell.vue";
</script>

<template>
  <GuideShell
    title="Comment choisir un VTT d'occasion en 2026"
    description="Guide complet pour acheter un VTT enduro, descente ou all-mountain d'occasion sans se faire avoir : checklist mécanique, signaux d'alerte, négociation."
    slug="comment-choisir-vtt-occasion"
    last-update="30 avril 2026"
    :reading-min="8"
  >
    <p>
      Acheter un VTT d'occasion, c'est diviser le prix par deux ou trois par rapport au neuf — mais c'est aussi
      hériter de la mécanique de quelqu'un qui peut-être a chargé sans pitié pendant trois saisons. Voici la
      méthode qu'on applique chez Trouve Ton VTT pour repérer les vrais bons plans et éviter les pièges.
    </p>

    <h2>1. Définir son usage avant de chercher</h2>
    <p>
      Le pire achat, c'est un VTT inadapté à ce que tu vas vraiment en faire. Avant de regarder les annonces,
      réponds à ces 3 questions :
    </p>
    <ul>
      <li><strong>Quel terrain ?</strong> Sentiers de plaine et chemins forestiers (XC / trail), montée-descente technique en montagne (all-mountain / enduro), bike-park et gros lâchers (DH).</li>
      <li><strong>Quel budget ?</strong> Compte 800-2000 € pour un VTT d'occasion correct, 2000-4000 € pour du carbone récent, 4000+ € pour de l'enduro top de gamme ou de l'électrique récent.</li>
      <li><strong>Électrique ou musculaire ?</strong> Un VAE pèse 22-25 kg vs 13-15 kg pour un musculaire. Le VAE permet plus de descentes par sortie mais pèse au transport et à la révision (moteur, batterie).</li>
    </ul>

    <div class="callout">
      <strong>Notre conseil :</strong> si tu hésites entre enduro et all-mountain, vise un all-mountain
      polyvalent (140-150 mm de débattement). Tu pourras tout faire avec, sauf de la DH pure.
    </div>

    <h2>2. Décrypter le débattement et la géométrie</h2>
    <p>
      Le débattement (en mm) c'est ce que la suspension peut absorber. C'est <strong>la donnée n°1</strong>
      pour savoir à quoi un VTT est destiné :
    </p>
    <ul>
      <li><strong>100-120 mm</strong> : XC, cross-country. Léger, rapide, mais pas fait pour la grosse descente.</li>
      <li><strong>130-140 mm</strong> : trail / all-mountain. Polyvalent.</li>
      <li><strong>150-170 mm</strong> : enduro. Conçu pour pédaler à la montée et envoyer fort à la descente.</li>
      <li><strong>180-200 mm</strong> : descente / freeride. Pas fait pour pédaler.</li>
    </ul>
    <p>
      L'<strong>angle de direction</strong> compte aussi. En enduro moderne, on est entre 63° et 65°
      (plus c'est petit, plus c'est stable à haute vitesse mais pataud à la montée).
    </p>

    <h2>3. La checklist mécanique avant achat</h2>
    <p>
      C'est la partie qu'on ne saute jamais. Demande à essayer le vélo en personne, et passe ces 10 minutes
      avec lui.
    </p>

    <h3>Cadre</h3>
    <ul>
      <li><strong>Inspecte les zones de stress</strong> : tube horizontal sous la selle, jonction tube de direction / tube horizontal, bases (sous le pédalier), points de pivot de la suspension. Cherche les fissures, les bosses, les éraflures profondes (surtout sur le carbone).</li>
      <li><strong>Vérifie le numéro de série</strong> est lisible et non poinçonné. Un cadre meulé = vol probable.</li>
      <li><strong>Carbone</strong> : tape doucement avec ton ongle sur les zones suspectes. Un son creux ou différent à un endroit = délamination potentielle.</li>
    </ul>

    <h3>Suspension</h3>
    <ul>
      <li><strong>Fourche</strong> : compresse-la à fond, écoute les bruits métalliques. Cherche les fuites d'huile sur les plongeurs (cernes brunes ou film gras). Vérifie le sag (enfoncement au poids du rider).</li>
      <li><strong>Amortisseur arrière</strong> : pareil, fuites d'huile, bruits anormaux. Un amorto qui revient lentement après compression = à reviser (~150-250 €).</li>
      <li><strong>Date de la dernière révision suspension</strong> : c'est typiquement tous les 100-200 h de roulage. Si le vendeur ne sait pas dire, c'est mauvais signe.</li>
    </ul>

    <h3>Roues et pneus</h3>
    <ul>
      <li><strong>Voilage</strong> : fait tourner la roue, regarde si elle est droite. Un voilage léger se rectifie (15-30 €), un voilage prononcé = jante à changer.</li>
      <li><strong>Roulements de moyeux</strong> : tiens l'axe et fait pivoter, ça doit être fluide sans à-coups. Si ça craque, roulements à changer (50-150 € selon roues).</li>
      <li><strong>Pneus</strong> : usure des crampons, fissures sur les flancs. Compte 60-100 € la paire si à changer.</li>
    </ul>

    <h3>Transmission</h3>
    <ul>
      <li><strong>Plateau et cassette</strong> : si les dents sont en forme de "vague" ou en pointe, c'est usé. Compte 80-200 € pour remplacer plateau + cassette + chaîne.</li>
      <li><strong>Chaîne</strong> : utilise un pied à coulisse ou la règle "chain checker". Au-delà de 0,75% d'allongement, c'est à changer (et probablement la cassette aussi si tu attends trop).</li>
      <li><strong>Dérailleur arrière</strong> : pas tordu (vérifie en alignant l'œil avec la chaîne par derrière). Le passage des vitesses doit être net, sans hésitation.</li>
    </ul>

    <h3>Freins</h3>
    <ul>
      <li><strong>Plaquettes</strong> : doivent avoir au moins 1 mm d'épaisseur. Sinon, 30-50 € la paire.</li>
      <li><strong>Disques</strong> : pas voilés (regarde-les tourner), pas trop fins (~1,5 mm minimum). Sinon 30-60 € pièce.</li>
      <li><strong>Dureté du levier</strong> : doit être ferme. Levier mou = purge à faire (50-80 € en magasin) ou pire, joint à changer.</li>
    </ul>

    <div class="callout-warn">
      <strong>⚠️ Signal d'alerte majeur :</strong> un vélo qui couine, claque, ou frotte au pédalage léger.
      Ça peut être bénin (boîtier de pédalier à graisser, 30 €), ou catastrophique (roulement de pivot
      principal HS, 200-500 € de réparation).
    </div>

    <h2>4. Spécificités VTT électrique</h2>
    <p>
      Si tu pars sur un VAE, ajoute ces 3 points à la checklist :
    </p>
    <ul>
      <li><strong>État de la batterie</strong> : demande le nombre de cycles (visible dans l'app constructeur Bosch / Shimano / Specialized). Au-delà de 500 cycles, autonomie ~70% ; au-delà de 1000, c'est à changer (700-1500 €).</li>
      <li><strong>Mises à jour firmware</strong> : à jour = signe d'un proprio sérieux.</li>
      <li><strong>Garantie résiduelle</strong> : le moteur Bosch CX a 2 ans de garantie. Demande la facture d'origine, elle peut être transférée si elle est dans la fenêtre.</li>
    </ul>

    <h2>5. Évaluer le prix : nos repères</h2>
    <p>
      Un VTT d'occasion cohérent décote d'environ <strong>40-50% sur les 3 premières années</strong>, puis
      ralentit (10-15% par an). Quelques repères en 2026 :
    </p>
    <ul>
      <li>Enduro carbone haut de gamme 2022-2023 (Nukeproof Mega, Commencal Meta, Specialized Enduro) : 2500-4000 €</li>
      <li>All-mountain alu 2020-2022 (Trek Fuel EX, Lapierre Zesty) : 1200-2200 €</li>
      <li>VTTAE Bosch CX 2021-2023 : 2500-4500 € selon usure batterie</li>
      <li>DH 2019-2022 (Commencal Supreme, Canyon Sender) : 1800-3500 €</li>
    </ul>
    <p>
      Si une annonce est <strong>30% sous le marché</strong>, deux possibilités : tu as trouvé un proprio
      pressé (vacances, déménagement, blessure), ou il y a un vice caché. Insiste sur le pourquoi du prix.
    </p>

    <h2>6. Sécuriser la transaction</h2>
    <ul>
      <li><strong>Ne jamais acheter sans voir le vélo</strong>. Les arnaques type "je l'envoie après virement" sont massives sur LBC.</li>
      <li><strong>Demande la facture d'origine</strong>. Sans facture, en cas de vol antérieur tu peux te retrouver sans recours.</li>
      <li><strong>Vérifie le numéro de série dans le fichier <a href="https://www.bicycode.org" target="_blank" rel="noopener" class="link-accent">Bicycode</a></strong> : si le vélo y est marqué et qu'il est déclaré volé, fuis.</li>
      <li><strong>Paye en espèces ou par virement</strong> au moment de récupérer le vélo. Évite PayPal "amis et famille" qui n'a aucune protection.</li>
      <li><strong>Photo du vélo + carte d'identité du vendeur + signature manuscrite</strong> sur un document de cession. Un modèle simple suffit (date, vélo, marque, modèle, numéro de série, prix, identités des deux parties).</li>
    </ul>

    <h2>7. La négociation</h2>
    <p>
      Sur LBC, presque toutes les annonces sont négociables. Compte <strong>10 à 20% de marge</strong> en moyenne.
      Pour bien négocier :
    </p>
    <ul>
      <li>Liste les points qui justifient une baisse (pneus à changer, suspension à reviser, plaquettes neuves à mettre).</li>
      <li>Compare avec d'autres annonces du même modèle.</li>
      <li>Reste poli, factuel — pas de bluff agressif. Les vendeurs préfèrent vendre à quelqu'un de sympa pour 100 € de moins.</li>
      <li>Utilise notre score IA dans tes arguments : "le marché ce vélo, c'est plutôt 1800 €".</li>
    </ul>

    <h2>En résumé</h2>
    <p>
      Le bon achat d'occasion, c'est <strong>un usage clair</strong>, <strong>une checklist méthodique</strong>,
      et <strong>une vérif terrain</strong>. Notre site fait le premier tri pour toi : on score chaque annonce
      VTT enduro et DH par rapport au prix marché. À toi de faire la vérif mécanique le jour J.
    </p>
  </GuideShell>
</template>
