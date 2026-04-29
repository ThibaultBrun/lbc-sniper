<script setup lang="ts">
import GuideShell from "./GuideShell.vue";
</script>

<template>
  <GuideShell
    title="Décrypter une annonce VTT sur Le Bon Coin : les pièges à éviter"
    description="Reconnaître les annonces honnêtes, les arnaques et les vélos volés sur Le Bon Coin. Questions à poser, signaux d'alerte, vérifications avant achat."
    slug="decrypter-annonce-leboncoin"
    last-update="30 avril 2026"
    :reading-min="7"
  >
    <p>
      Sur Le Bon Coin, sur 100 annonces VTT, environ 5 sont des arnaques pures, 10 sont des vélos volés
      (souvent à l'insu du vendeur de bonne foi qui l'a acheté à un voleur), et le reste est honnête.
      Voici comment trier en 2 minutes par annonce.
    </p>

    <h2>Les 7 signaux d'alerte à reconnaître</h2>

    <h3>1. Le prix anormalement bas</h3>
    <p>
      Si une annonce affiche un VTT à <strong>50% sous le marché</strong>, méfiance maximale. Les raisons
      légitimes existent (urgence financière, déménagement, blessure, divorce), mais 8 fois sur 10 c'est :
    </p>
    <ul>
      <li>Une <strong>arnaque</strong> où le vendeur veut juste capter ton acompte par virement</li>
      <li>Un <strong>vélo volé</strong> que le vendeur veut écouler vite</li>
      <li>Un <strong>vélo cassé</strong> qu'il ne veut pas mentionner</li>
    </ul>
    <p>
      Notre score IA t'aide ici : si on annonce un score "trop beau pour être vrai", lis bien la description
      avant de te précipiter.
    </p>

    <h3>2. Photos volées ou stock</h3>
    <p>
      Avant tout contact, fais un <strong>Google Image reverse search</strong> sur les photos de l'annonce
      (clic droit → "Rechercher l'image avec Google"). Si tu retrouves les mêmes photos sur :
    </p>
    <ul>
      <li>Un site de vente neuf (Alltricks, Probikeshop, site marque) → photos de stock, le vendeur n'a peut-être pas le vélo</li>
      <li>Une autre annonce LBC avec un autre vendeur → arnaque, ils volent les photos d'annonces réelles</li>
      <li>Un forum ou un Pinterest → potentiellement annonce factice</li>
    </ul>

    <h3>3. Description vague ou copiée-collée</h3>
    <p>
      Une annonce honnête a <strong>du détail spécifique</strong> : "fourche Fox 36 Performance Elite révisée
      en mars 2026, plaquettes neuves, pneus Maxxis Assegai 2.5 à 70%". Une annonce arnaque a souvent une
      description courte, générique, ou copie le descriptif officiel du constructeur.
    </p>

    <h3>4. Vendeur récent ou sans historique</h3>
    <p>
      Sur LBC, regarde le profil du vendeur. Une seule annonce, compte créé il y a 2 jours, pas d'autres
      ventes : prudence. Un compte avec 50 annonces sur 5 ans dans le vélo + d'autres trucs (jardinage,
      mobilier, etc.) c'est rassurant — c'est un vrai humain qui vend ses trucs.
    </p>

    <h3>5. Localisation floue ou changeante</h3>
    <p>
      Si le vendeur dit "je suis en déplacement, j'envoie le vélo par transporteur", c'est <strong>arnaque
      classique</strong>. Aucun particulier honnête ne propose ça en premier — ils veulent que tu viennes
      voir le vélo.
    </p>
    <p>
      Variante : "le vélo est chez ma sœur à Bordeaux mais je vis à Paris, je peux te l'envoyer". Refuse,
      ça sent l'embrouille.
    </p>

    <h3>6. Demande de paiement avant rencontre</h3>
    <p>
      <strong>Règle d'or :</strong> tu ne payes JAMAIS avant d'avoir vu et essayé le vélo. Toute personne qui
      demande un acompte par PayPal "amis et famille", virement, ou pire, par mandat cash type Western Union,
      est en train d'arnaquer.
    </p>

    <h3>7. Communication uniquement par mail / WhatsApp / hors LBC</h3>
    <p>
      Les arnaqueurs essaient toujours de sortir de la messagerie LBC vers un canal moins traçable. "Réponds
      moi sur WhatsApp au +33 6 XX XX XX XX" en 2e message = signal rouge. Les pros et particuliers honnêtes
      restent sur LBC ou donnent un téléphone fixe vérifiable.
    </p>

    <h2>Les questions à poser systématiquement</h2>
    <p>
      Avant de te déplacer, envoie ces 5 questions (un vendeur honnête y répond en 30 minutes) :
    </p>
    <ol>
      <li><strong>"As-tu la facture d'origine ?"</strong> — sans facture, tu n'as aucune preuve d'achat licite. Réponse "elle est dans un carton chez mes parents" = méfiance.</li>
      <li><strong>"Quel est le numéro de série du cadre ?"</strong> — tu pourras le vérifier sur Bicycode et autres bases vol.</li>
      <li><strong>"Quand a été faite la dernière révision suspension ?"</strong> — un vrai propriétaire sait répondre.</li>
      <li><strong>"Combien de cycles sur la batterie ?"</strong> (si VAE) — visible dans l'app constructeur. Réponse vague = mauvais signe.</li>
      <li><strong>"Pourquoi tu vends ?"</strong> — demande naïve mais qui filtre. "Je passe à un autre vélo / blessure / besoin d'argent" = OK ; "ne correspond plus à mes besoins" + flou = à creuser.</li>
    </ol>

    <h2>Vérifier qu'un vélo n'est pas volé</h2>
    <p>
      C'est la grosse hantise du marché de l'occasion : acheter un vélo volé, qui peut être saisi par la police
      des mois plus tard sans aucun recours pour toi. <strong>3 vérifications obligatoires</strong> :
    </p>
    <ul>
      <li>
        <strong>Bicycode (national, gratuit)</strong> :
        <a href="https://www.bicycode.org" target="_blank" rel="noopener" class="link-accent">bicycode.org</a>
        — depuis 2021, tous les vélos vendus en magasin sont marqués. Si un cadre porte un numéro Bicycode et qu'il
        est marqué volé, tu fuis.
      </li>
      <li>
        <strong>Bike Index (international)</strong> :
        <a href="https://bikeindex.org" target="_blank" rel="noopener" class="link-accent">bikeindex.org</a>
        — fichier mondial. Tape le numéro de série du cadre.
      </li>
      <li>
        <strong>Recherche Google du numéro de série</strong> — parfois les propriétaires diffusent sur Facebook,
        Reddit, forums quand ils se font voler. Une recherche "numero serie XYZ123 vol" peut sortir un post
        Facebook désespéré.
      </li>
    </ul>

    <div class="callout-warn">
      <strong>⚠️ Si le numéro de série est meulé, brûlé ou illisible :</strong> n'achète pas. Aucune raison
      légitime à ça. C'est le marqueur n°1 d'un vélo volé.
    </div>

    <h2>Le test des 3 minutes au téléphone</h2>
    <p>
      Avant de te déplacer pour un vélo cher, appelle le vendeur (oui, vraiment, parle-lui). Tu vas tester :
    </p>
    <ul>
      <li><strong>Sa connaissance du vélo</strong> : "tu peux me dire la taille du cadre ?", "c'est quoi la fourche ?", "quel groupe ?". Un vrai propriétaire répond sans hésiter.</li>
      <li><strong>Son langage</strong> : un arnaqueur a souvent un français bizarre, des structures de phrases traduites depuis l'anglais.</li>
      <li><strong>Sa logistique</strong> : "je passe quand pour voir le vélo ?". S'il esquive systématiquement, tu sais.</li>
    </ul>

    <h2>Le jour de l'achat : sécuriser la transaction</h2>
    <p>
      Tu y vas, le vélo est conforme, le prix est OK. Quelques règles :
    </p>
    <ul>
      <li><strong>Toujours en personne, jamais seul</strong> si possible (un copain en backup, ça refroidit les ardeurs).</li>
      <li><strong>Lieu public ou domicile du vendeur</strong> — pas un parking de zone industrielle isolé.</li>
      <li><strong>Vérification du numéro de série</strong> avec ce qu'il t'a dit au téléphone.</li>
      <li><strong>Demande sa carte d'identité</strong> et compare avec le nom sur la facture si tu l'as.</li>
      <li><strong>Acte de cession écrit</strong> (modèle simple disponible sur internet) avec : date, identités des deux parties, vélo (marque, modèle, numéro de série), prix, signatures.</li>
      <li><strong>Paiement</strong> : espèces si < 1500 €, virement instantané sinon (le virement est pas annulable, mais il est traçable). Évite les chèques (peuvent être annulés, peuvent être volés).</li>
    </ul>

    <div class="callout">
      <strong>Astuce pratique :</strong> garde tous les échanges LBC + WhatsApp en captures d'écran. Et photographie
      le vélo lors de l'achat avec sa carte ID dans le cadre. En cas de litige, ça sert.
    </div>

    <h2>Si tu te fais arnaquer : que faire ?</h2>
    <p>
      Si malgré tout ça tu es victime d'une arnaque, voici la marche à suivre :
    </p>
    <ol>
      <li><strong>Plainte au commissariat</strong> dans les 24-48h, avec toutes les preuves (échanges, captures, factures, virements).</li>
      <li><strong>Signalement Pharos</strong> (
        <a href="https://www.internet-signalement.gouv.fr" target="_blank" rel="noopener" class="link-accent">internet-signalement.gouv.fr</a>
        ).</li>
      <li><strong>Signalement à LBC</strong> via leur formulaire — ils peuvent bloquer le compte du vendeur si récidive.</li>
      <li><strong>Si paiement par carte ou virement</strong> : contacte ta banque pour tenter une opposition / chargeback. Difficile mais possible si action rapide.</li>
    </ol>

    <h2>En résumé : la règle des 3 NON</h2>
    <ol>
      <li>Pas d'argent <strong>avant</strong> de voir.</li>
      <li>Pas de transaction <strong>hors LBC / hors face-à-face</strong>.</li>
      <li>Pas d'achat <strong>sans facture ni numéro de série lisible</strong>.</li>
    </ol>
    <p>
      Si tu coches ces 3 cases, tu es protégé contre 95% des arnaques et 80% des vols. Notre score IA t'aide
      à filtrer les bonnes affaires, mais la sécurité de la transaction reste ton boulot. Bon ride.
    </p>
  </GuideShell>
</template>
