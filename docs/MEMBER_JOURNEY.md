# Parcours membre Aide Bot

## Objectif

Aide Bot doit rester simple côté membre même si le système interne est complet. En quelques secondes, une personne doit comprendre ce qu’elle peut apprendre, comment demander de l’aide, comment débloquer une formation et comment contribuer ensuite à la communauté.

## Entrée principale

`/centre` ouvre le centre membre interactif avec cinq actions :

- voir les formations ;
- demander de l’aide ;
- voir son profil et sa prochaine étape ;
- voir ses invitations/récompenses ;
- commencer à aider la communauté.

`/commencer` donne une recommandation personnalisée selon les crédits d’invitation, les formations terminées, les aides réalisées, la réputation et le statut Helper.

## Formations classiques

Les parcours classiques sont débloqués avec 1 invitation valide :

- Débuter sur Discord ;
- Créer son premier serveur ;
- Permissions, modération et sécurité ;
- Créer son premier bot Discord.

Chaque parcours expose un niveau, une durée indicative et des étapes claires. `/parcours formation:<clé>` affiche le programme détaillé.

## VIP et extensions

Les offres payantes restent soumises à une confirmation humaine du staff :

- Formation VIP / accompagnement sur mesure ;
- Extension VIP — Serveur professionnel ;
- Extension VIP — Bot avancé ;
- Extension VIP — Sécurité avancée.

Aucune formation VIP ne peut être prise par un Formateur tant que le paiement n’est pas marqué payé.

## Entraide communautaire

Le chemin normal est :

`/chercher` → si insuffisant `/aide demander` → Helper/Formateur → résolution → réputation/avis.

Les membres compétents peuvent renseigner leurs compétences, devenir disponibles et candidater pour devenir Helper/Formateur.

## Progression

Le profil montre :

- niveau communauté ;
- réputation ;
- personnes aidées ;
- formations terminées ;
- note moyenne ;
- compétences ;
- badges ;
- prochaine action recommandée.

Les challenges permettent de pratiquer au lieu de seulement lire ou écouter une formation.

## Invitations

Les invitations sont validées après le délai configuré. Les récompenses actuelles sont :

- 1 invitation : formation classique débloquée ;
- 3 invitations : pack de presets bonus ;
- 5 invitations : mini-formation bonus ;
- 10 invitations : badge/rôle Ambassadeur.

`/recompenses` indique le total, les crédits encore utilisables et le prochain palier.

## Principe de permissions

Les rôles Helper et Formateur ne reçoivent aucune permission Discord sensible par défaut. Les actions du bot passent par des capacités explicites et fail-closed. Aucun rôle canonique ne reçoit `Administrateur` ni `Gérer le serveur` par défaut.
