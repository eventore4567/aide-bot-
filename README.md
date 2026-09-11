# Aide Bot

Aide Bot est une plateforme Discord d’apprentissage, d’entraide et de formation pensée pour les débutants comme pour les membres avancés.

Le projet combine un serveur compact (15 salons permanents maximum), un bot central, des formations, de l’entraide communautaire, des profils, de la réputation, des Helpers/Formateurs, des invitations validées et une gestion stricte des permissions.

## Parcours membre

`Rejoindre -> Découvrir -> Choisir -> Formulaire -> Ticket -> Helper/Formateur -> Planning -> Progression -> Ressources -> Exercice -> Avis -> Badge -> Aider les autres`

## Offre

- Formation classique : déblocage par **1 invitation valide** (validation différée pour limiter les faux comptes).
- Paliers bonus : 3 invitations = ressources supplémentaires, 5 invitations = mini-formation bonus.
- Formation VIP / extensions : suivi premium, vocal, sécurité avancée, bot Discord, audit de serveur, mentorat, etc. Le paiement reste confirmé manuellement par le staff.
- Entraide communautaire gratuite : les membres compétents peuvent devenir Helpers et prendre des demandes.

## Fonctionnalités V1

- `/setup` idempotent : crée la structure du serveur sans supprimer l’existant.
- 15 salons permanents max, rôles et permissions propres.
- Panneau de formations + formulaires.
- Tickets privés.
- Attribution d’un Formateur/Helper.
- Progression étape par étape.
- Planning et rendez-vous.
- Paiement marqué `en attente / payé / terminé` par le staff.
- Ressources et presets.
- Avis clients.
- Profils, réputation, compétences et disponibilité Helper.
- Invitations avec validation différée.
- Candidatures Helper/Formateur.
- Diagnostic `/permissions_test`.
- Logs et statistiques staff.

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

## Railway

Le service Railway `aide-bot-` est déjà relié au dépôt `eventore4567/aide-bot-`. Le déploiement reste volontairement bloqué tant que `DISCORD_TOKEN` n’est pas configuré.

## Documentation

- `docs/CONCEPT.md` — vision complète
- `docs/SERVER.md` — rôles + salons
- `docs/PERMISSIONS.md` — modèle fail-closed
- `docs/ROADMAP.md` — phases du projet
