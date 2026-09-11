# Exploitation Aide Bot

## Panneau membre permanent

Le salon `🎫・commencer` reçoit un panneau interactif unique identifié par le marqueur interne `AIDEBOT_MEMBER_HUB_V1`.

Le bot vérifie l’historique avant de créer un panneau. S’il ne peut pas lire l’historique, il n’en crée pas un nouveau afin d’éviter les doublons à chaque reconnexion.

Le panneau expose les accès principaux : formations, aide, profil, récompenses et contribution communautaire.

## Suivi opérationnel staff

Le salon `🧠・suivi-formations` contient un dashboard unique identifié par `AIDEBOT_OPS_DASHBOARD_V1`.

Il est actualisé automatiquement toutes les cinq minutes et affiche :

- demandes ouvertes ;
- formations / aides actives ;
- Helpers disponibles ;
- candidatures en attente ;
- challenges à vérifier ;
- mentorats ouverts / actifs ;
- rappels en attente ;
- nombre et moyenne des avis ;
- état opérationnel et priorité suggérée.

Le dashboard peut aussi être actualisé avec `/dashboard_actualiser` par les rôles disposant de `dashboard.view`.

La Direction peut utiliser `/panneaux_actualiser` pour réconcilier le dashboard et le centre membre.

## Mentions

Aide Bot utilise `AllowedMentions.none()` globalement. Les mentions peuvent donc être affichées dans les messages et les logs sans déclencher de ping inattendu. Une fonctionnalité qui aurait besoin d’un vrai ping devra l’autoriser explicitement au niveau du message concerné.

## Présence

Quand le bot est connecté, sa présence indique `Apprendre • /centre` pour orienter les nouveaux vers l’entrée principale.
