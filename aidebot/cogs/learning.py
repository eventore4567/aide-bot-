from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from aidebot.catalog import CHALLENGES, INVITE_REWARDS, KNOWLEDGE_BASE, RESOURCES, invite_reward_for, search_knowledge
from aidebot.challenge_workflow import challenge_already_completed, resolve_challenge_atomic
from aidebot.permissions import can


def _embed(title: str, description: str, color: int = 0x5865F2) -> discord.Embed:
    return discord.Embed(title=title, description=description, color=color)


async def _audit(guild: discord.Guild, title: str, description: str) -> None:
    channel = discord.utils.get(guild.text_channels, name="🧾・logs")
    if channel:
        await channel.send(embed=_embed(title, description, 0x2B2D31))


class LearningCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    favoris = app_commands.Group(name="favoris", description="Tes ressources sauvegardées")
    challenge = app_commands.Group(name="challenge", description="Challenges pratiques Aide Bot")
    mentorat = app_commands.Group(name="mentorat", description="Mentorat communautaire")

    @app_commands.command(name="chercher", description="Chercher une réponse dans le centre de connaissances")
    @app_commands.describe(question="Ex: comment sécuriser le token de mon bot ?")
    async def chercher(self, interaction: discord.Interaction, question: str) -> None:
        results = search_knowledge(question)
        if not results:
            return await interaction.response.send_message(
                "Je n’ai pas trouvé de ressource correspondante. Essaie `/aide demander` pour demander à la communauté.",
                ephemeral=True,
            )
        lines = []
        for key, item in results:
            lines.append(f"**{item['title']}** (`{key}`)\n{item['summary']}")
        await interaction.response.send_message(embed=_embed("Centre de connaissances", "\n\n".join(lines)), ephemeral=True)

    @favoris.command(name="ajouter", description="Ajouter une ressource à tes favoris")
    async def favoris_ajouter(self, interaction: discord.Interaction, ressource: str) -> None:
        if not interaction.guild:
            return
        key = ressource.casefold().strip()
        if key not in KNOWLEDGE_BASE and key not in RESOURCES:
            return await interaction.response.send_message("Ressource inconnue. Utilise `/chercher` pour trouver une clé valide.", ephemeral=True)
        created = await self.bot.db.add_favorite(interaction.guild.id, interaction.user.id, key)
        message = "Ajouté à tes favoris." if created else "Cette ressource est déjà dans tes favoris."
        await interaction.response.send_message(message, ephemeral=True)

    @favoris.command(name="retirer", description="Retirer une ressource de tes favoris")
    async def favoris_retirer(self, interaction: discord.Interaction, ressource: str) -> None:
        if not interaction.guild:
            return
        removed = await self.bot.db.remove_favorite(interaction.guild.id, interaction.user.id, ressource.casefold().strip())
        await interaction.response.send_message("Favori retiré." if removed else "Cette ressource n’était pas dans tes favoris.", ephemeral=True)

    @favoris.command(name="liste", description="Voir tes ressources favorites")
    async def favoris_liste(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        keys = await self.bot.db.favorites(interaction.guild.id, interaction.user.id)
        if not keys:
            return await interaction.response.send_message("Tu n’as encore aucun favori.", ephemeral=True)
        labels = []
        for key in keys:
            if key in KNOWLEDGE_BASE:
                labels.append(f"• `{key}` — {KNOWLEDGE_BASE[key]['title']}")
            else:
                labels.append(f"• `{key}` — ressource rapide")
        await interaction.response.send_message(embed=_embed("Tes favoris", "\n".join(labels)), ephemeral=True)

    @challenge.command(name="liste", description="Voir les challenges disponibles")
    async def challenge_liste(self, interaction: discord.Interaction) -> None:
        lines = [
            f"**{data['title']}** (`{key}`) — {data['difficulty']} • +{data['reward']} réputation\n{data['description']}"
            for key, data in CHALLENGES.items()
        ]
        await interaction.response.send_message(embed=_embed("Challenges pratiques", "\n\n".join(lines)), ephemeral=True)

    @challenge.command(name="envoyer", description="Envoyer la preuve d’un challenge terminé")
    @app_commands.describe(challenge="Clé du challenge", preuve="Lien, explication ou éléments permettant au staff de vérifier")
    async def challenge_envoyer(self, interaction: discord.Interaction, challenge: str, preuve: str) -> None:
        if not interaction.guild:
            return
        key = challenge.casefold().strip()
        if key not in CHALLENGES:
            return await interaction.response.send_message("Challenge inconnu. Utilise `/challenge liste`.", ephemeral=True)
        if await challenge_already_completed(self.bot.db._db(), interaction.guild.id, interaction.user.id, key):
            return await interaction.response.send_message(
                "Ce challenge est déjà validé sur ton profil. La récompense ne peut être obtenue qu’une seule fois.",
                ephemeral=True,
            )
        submission_id = await self.bot.db.submit_challenge(interaction.guild.id, interaction.user.id, key, preuve[:1500])
        if submission_id is None:
            return await interaction.response.send_message("Tu as déjà une soumission en attente pour ce challenge.", ephemeral=True)
        staff = discord.utils.get(interaction.guild.text_channels, name="📋・staff")
        if staff:
            await staff.send(embed=_embed(
                f"Challenge #{submission_id} à vérifier",
                f"**Membre :** {interaction.user.mention}\n**Challenge :** {CHALLENGES[key]['title']} (`{key}`)\n**Preuve :** {preuve[:1500]}\n\nValidation : `/challenge valider id:{submission_id} accepte:True`",
                0xF1C40F,
            ))
        await _audit(interaction.guild, "Challenge envoyé", f"#{submission_id} • {interaction.user.mention} • `{key}`")
        await interaction.response.send_message(f"Soumission **#{submission_id}** envoyée au staff.", ephemeral=True)

    @challenge.command(name="valider", description="Valider ou refuser une soumission de challenge")
    async def challenge_valider(self, interaction: discord.Interaction, id: int, accepte: bool) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not can(interaction.user, "challenge.review"):
            return await interaction.response.send_message("Accès refusé : `challenge.review` requis.", ephemeral=True)
        row = await self.bot.db.challenge_submission(id)
        if not row or row["guild_id"] != interaction.guild.id:
            return await interaction.response.send_message("Soumission introuvable.", ephemeral=True)
        if row["status"] != "pending":
            return await interaction.response.send_message("Cette soumission a déjà été traitée.", ephemeral=True)
        reward = int(CHALLENGES.get(row["challenge_key"], {}).get("reward", 0))
        result = await resolve_challenge_atomic(
            self.bot.db._db(),
            submission_id=id,
            guild_id=interaction.guild.id,
            reviewer_id=interaction.user.id,
            accepted=accepte,
            reward=reward,
        )
        if not result.changed:
            return await interaction.response.send_message("Cette soumission a été traitée entre-temps.", ephemeral=True)
        await _audit(interaction.guild, "Challenge traité", f"#{id} • {'accepté' if accepte else 'refusé'} par {interaction.user.mention}")
        await interaction.response.send_message(f"Challenge **{'accepté' if accepte else 'refusé'}**." + (f" +{reward} réputation." if accepte else ""), ephemeral=True)

    @mentorat.command(name="demander", description="Demander un mentor pour progresser sur un sujet")
    async def mentorat_demander(self, interaction: discord.Interaction, sujet: str) -> None:
        if not interaction.guild:
            return
        mentorship_id = await self.bot.db.create_mentorship(interaction.guild.id, interaction.user.id, sujet[:300])
        if mentorship_id is None:
            return await interaction.response.send_message("Tu as déjà une demande de mentorat ouverte ou active.", ephemeral=True)
        entraide = discord.utils.get(interaction.guild.text_channels, name="🆘・entraide")
        if entraide:
            await entraide.send(embed=_embed(
                f"Mentorat #{mentorship_id}",
                f"{interaction.user.mention} cherche un mentor.\n**Sujet :** {sujet[:300]}\n\nUn Helper/Formateur peut utiliser `/mentorat prendre id:{mentorship_id}`.",
                0x57F287,
            ))
        await _audit(interaction.guild, "Demande de mentorat", f"#{mentorship_id} • {interaction.user.mention}")
        await interaction.response.send_message(f"Demande de mentorat **#{mentorship_id}** créée.", ephemeral=True)

    @mentorat.command(name="prendre", description="Prendre une demande de mentorat")
    async def mentorat_prendre(self, interaction: discord.Interaction, id: int) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not can(interaction.user, "mentorship.claim"):
            return await interaction.response.send_message("Accès refusé : `mentorship.claim` requis.", ephemeral=True)
        row = await self.bot.db.mentorship(id)
        if not row or row["guild_id"] != interaction.guild.id:
            return await interaction.response.send_message("Mentorat introuvable.", ephemeral=True)
        if row["student_id"] == interaction.user.id:
            return await interaction.response.send_message("Tu ne peux pas être ton propre mentor.", ephemeral=True)
        if not await self.bot.db.claim_mentorship(id, interaction.user.id):
            return await interaction.response.send_message("Cette demande n’est plus disponible.", ephemeral=True)
        await _audit(interaction.guild, "Mentorat attribué", f"#{id} • mentor {interaction.user.mention} • élève <@{row['student_id']}>")
        await interaction.response.send_message(f"Tu es maintenant mentor de <@{row['student_id']}> pour **{row['topic']}**.")

    @mentorat.command(name="terminer", description="Terminer un mentorat actif")
    async def mentorat_terminer(self, interaction: discord.Interaction, id: int) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        row = await self.bot.db.mentorship(id)
        if not row or row["guild_id"] != interaction.guild.id:
            return await interaction.response.send_message("Mentorat introuvable.", ephemeral=True)
        allowed = interaction.user.id in {row["student_id"], row["mentor_id"]} or can(interaction.user, "training.manage")
        if not allowed:
            return await interaction.response.send_message("Tu ne peux pas terminer ce mentorat.", ephemeral=True)
        completed = await self.bot.db.complete_mentorship_once(id, interaction.guild.id)
        if completed is None:
            return await interaction.response.send_message("Ce mentorat n’est pas actif ou a déjà été terminé.", ephemeral=True)
        await _audit(interaction.guild, "Mentorat terminé", f"#{id} • terminé par {interaction.user.mention}")
        await interaction.response.send_message("Mentorat terminé. Le mentor reçoit **+30 réputation**.")

    @app_commands.command(name="bonus_invites", description="Voir tes invitations et les récompenses communautaires")
    async def bonus_invites(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        total = await self.bot.db.validated_invites(interaction.guild.id, interaction.user.id)
        credits = await self.bot.db.invite_credits(interaction.guild.id, interaction.user.id)
        lines = []
        for threshold, label in INVITE_REWARDS:
            icon = "✅" if total >= threshold else "🔒"
            lines.append(f"{icon} **{threshold} invitation(s)** — {label}")
        desc = f"**Invitations validées :** {total}\n**Crédits disponibles :** {credits}\n**Meilleure récompense :** {invite_reward_for(total)}\n\n" + "\n".join(lines)
        await interaction.response.send_message(embed=_embed("Récompenses d’invitations", desc), ephemeral=True)

    @app_commands.command(name="classement", description="Voir les membres les plus utiles de la communauté")
    async def classement(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            return
        rows = await self.bot.db.leaderboard(interaction.guild.id, 10)
        if not rows:
            return await interaction.response.send_message("Le classement est encore vide.", ephemeral=True)
        lines = []
        for index, row in enumerate(rows, 1):
            lines.append(f"**{index}.** <@{row['user_id']}> — **{row['reputation']}** rep • {row['helped_count']} aides • {row['trainings_completed']} formations")
        await interaction.response.send_message(embed=_embed("Classement communauté", "\n".join(lines)))

    @app_commands.command(name="dashboard", description="Voir l’état opérationnel des formations et de l’entraide")
    async def dashboard(self, interaction: discord.Interaction) -> None:
        if not interaction.guild or not isinstance(interaction.user, discord.Member):
            return
        if not can(interaction.user, "dashboard.view"):
            return await interaction.response.send_message("Accès refusé : `dashboard.view` requis.", ephemeral=True)
        stats = await self.bot.db.dashboard_stats(interaction.guild.id)
        desc = (
            f"**Demandes ouvertes :** {stats['open_requests']}\n"
            f"**Formations/aides actives :** {stats['active_trainings']}\n"
            f"**Challenges à vérifier :** {stats['pending_challenges']}\n"
            f"**Mentorats ouverts/actifs :** {stats['open_mentorships']}\n"
            f"**Helpers disponibles :** {stats['available_helpers']}\n"
            f"**Avis :** {stats['reviews']} • moyenne **{stats['avg_rating']:.1f}/5**"
        )
        await interaction.response.send_message(embed=_embed("Dashboard Aide Bot", desc, 0x57F287), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LearningCog(bot))
