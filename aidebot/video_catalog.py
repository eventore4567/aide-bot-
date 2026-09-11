from __future__ import annotations

from aidebot.experience_content import VIDEO_LIBRARY as BASE_VIDEO_LIBRARY


VIDEO_LIBRARY = {
    **BASE_VIDEO_LIBRARY,
    "webhooks": {
        "title": "Webhooks & embeds Discord — guide visuel",
        "url": "https://www.youtube.com/watch?v=d7wqzkvdREI",
        "note": "Créer un webhook, comprendre les embeds et éviter les erreurs de mise en forme. Utile pour les annonces, logs et panneaux propres.",
    },
    "railway": {
        "title": "Héberger un bot Python sur Railway",
        "url": "https://www.youtube.com/watch?v=8W4kiy20xps",
        "note": "Support visuel sur le déploiement d’un bot Python. Les écrans peuvent évoluer : garde les secrets dans les variables et utilise un stockage persistant pour les données.",
    },
    "slash": {
        "title": "discord.py — commandes slash",
        "url": "https://www.youtube.com/watch?v=CLQ8gfb2jh4",
        "note": "Complément pour comprendre le principe des slash commands et la synchronisation des commandes dans Discord.",
    },
    "tickets": {
        "title": "Tickets Discord — chercher un tutoriel récent",
        "url": "https://www.youtube.com/results?search_query=discord+tickets+bot+tutoriel+francais",
        "note": "Sélection YouTube pour voir plusieurs systèmes de tickets. Compare toujours la confidentialité des salons, les permissions et la fermeture propre.",
    },
    "security": {
        "title": "Sécurité / anti-raid Discord — tutoriels récents",
        "url": "https://www.youtube.com/results?search_query=discord+securite+anti+raid+tutoriel+francais",
        "note": "Sélection visuelle sur la sécurité serveur. Ne copie pas une configuration sans vérifier les permissions sensibles et la hiérarchie des rôles.",
    },
    "github": {
        "title": "Git & GitHub — bases pour gérer ton bot",
        "url": "https://www.youtube.com/results?search_query=git+github+debutant+tutoriel+francais",
        "note": "Comprendre commits, branches, push et pull requests pour travailler proprement sans modifier directement la production.",
    },
}
