# Aide Bot

Aide Bot est une plateforme Discord d’apprentissage, d’entraide et de formation pensée pour les débutants comme pour les membres avancés.

Le projet combine un serveur compact (15 salons permanents maximum), un bot central, des formations, de l’entraide communautaire, des profils, de la réputation, des Helpers/Formateurs, des invitations validées et une gestion stricte des permissions.

## Parcours membre

`Rejoindre -> Découvrir -> Choisir -> Formulaire -> Ticket -> Helper/Formateur -> Planning -> Progression -> Ressources -> Exercice -> Avis -> Badge -> Aider les autres`

## Offre

- Formation classique : déblocage par **1 invitation valide** (validation différée pour limiter les faux comptes).
- Paliers bonus : 3 invitations = ressources supplémentaires, 5 invitations = mini-formation bonus, 10 invitations = rôle Ambassadeur.
- Formation VIP / extensions : suivi premium, vocal, sécurité avancée, bot Discord, audit de serveur, mentorat, etc. Le paiement reste confirmé manuellement par le staff.
- Entraide communautaire gratuite : les membres compétents peuvent devenir Helpers et prendre des demandes.

## Fonctionnalités actuelles

- `/setup` idempotent : crée et réconcilie la structure du serveur sans supprimer l’existant.
- 15 salons permanents max, rôles et permissions fail-closed.
- Panneau de formations + formulaires.
- Tickets privés, attribution Helper/Formateur, progression, archivage et avis.
- Planning et rappels automatiques persistés en base (`/formation_rappel`).
- Paiement VIP marqué `en attente / payé` par la Direction.
- Ressources, presets, centre de connaissances et favoris.
- Challenges pratiques + validation + réputation.
- Mentorat communautaire.
- Profils, niveaux, badges, réputation, compétences et disponibilité Helper.
- Recherche de Helpers disponibles selon leurs compétences (`/aide trouver_helper`).
- Invitations avec validation différée et récompenses.
- Candidatures Helper/Formateur enregistrées, listées et validées par le staff.
- Diagnostic `/permissions_test` et audit `/audit_serveur`.
- Dashboard, classement, logs et statistiques staff.
- Tests GitHub Actions sur la base, les permissions, la progression, les ressources et les principaux workflows.

## Démarrage local

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py
```

Variables minimales :

```env
DISCORD_TOKEN=...
GUILD_ID=...
```

Le bot utilise SQLite pour la V1 (`data/aidebot.db`). Sur Railway, ajoutez un volume persistant avant une vraie ouverture publique, ou migrez la couche de stockage vers PostgreSQL. Aucun secret ne doit être commité dans GitHub.

## Railway / Discord

Le service Railway `aide-bot-` est relié au dépôt `eventore4567/aide-bot-` et le token Discord est configuré.

Avant le prochain démarrage, **Server Members Intent** doit être activé dans Discord Developer Portal > Bot > Privileged Gateway Intents. Cet intent est requis pour les arrivées membres, le rôle automatique et la validation des invitations.

Les déploiements automatiques restent volontairement neutralisés pendant la phase de préparation afin de ne pas redéployer un service cassé à chaque commit.

## Bloquants avant ouverture publique

1. Activer **Server Members Intent** puis effectuer un démarrage réel sur Railway.
2. Ajouter un stockage persistant Railway (volume) ou PostgreSQL avant de conserver de vraies données membres.
3. Tester le parcours Discord complet : invitation -> formation -> attribution -> rappel -> progression -> avis -> candidature -> entraide.
4. Vérifier `/audit_serveur` après `/setup` sur le serveur cible.

## Documentation

- `docs/CONCEPT.md` — vision complète
- `docs/SERVER.md` — rôles + salons
- `docs/PERMISSIONS.md` — modèle fail-closed
- `docs/ROADMAP.md` — phases du projet
