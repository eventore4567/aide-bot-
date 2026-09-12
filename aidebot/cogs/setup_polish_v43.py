from __future__ import annotations

import discord
from discord.ext import commands

from aidebot.blueprint import CATEGORY_SPECS, ROLE_SPECS
from aidebot.cogs.setup_server import SetupServerCog
from aidebot.cogs.training_experience_v42 import training_catalog_embed
from aidebot.experience_content import BANNER_URL
from aidebot.setup_guard import canonical_collisions


def _training_embed_v44(self: SetupServerCog) -> discord.Embed:
    e = training_catalog_embed()
    e.title = "Aide Bot — Formations & parcours"
    e.description = (
        "Ce salon est un **catalogue de parcours**, pas une liste de commandes. Le membre choisit un sujet, lit sa fiche complète, "
        "voit le niveau, la durée, le programme, les résultats attendus et les ressources, puis ouvre seulement ensuite le formulaire adapté.\n\n"
        + (e.description or "")
    )[:4000]
    e.add_field(
        name="Avant de commencer",
        value="Lis la fiche du parcours, vérifie les prérequis et regarde les ressources recommandées. Le ticket sert ensuite au suivi, pas à découvrir ce que tu as acheté ou choisi.",
        inline=False,
    )
    e.set_footer(text="Aide Bot V44 • Fiche → ressources → formulaire → ticket → résultat")
    return e


def _staff_embed_v44(self: SetupServerCog) -> discord.Embed:
    e = discord.Embed(
        title="Aide Bot — Cockpit staff",
        description=(
            "Le staff travaille directement depuis les **tickets, candidatures et panneaux**. Les commandes internes restent invisibles aux membres.\n\n"
            "**Support** : lire le diagnostic → Prendre → répondre → avancer → Terminer → avis → archiver.\n"
            "**Formations** : respecter le programme affiché et valider chaque étape.\n"
            "**Premium** : vérifier le paiement avant prise en charge ; le rôle `💎・VIP` est attribué par le bot après validation.\n"
            "**Recrutement** : lire toute la candidature et le cas pratique avant Accepter / Refuser.\n"
            "**Sécurité** : aucun secret utilisateur ne doit être demandé, copié ou stocké."
        ),
        color=0xF1C40F,
    )
    e.add_field(
        name="Qualité de service",
        value="Un seul responsable par ticket. Toujours expliquer ce qui a été fait, pourquoi, et ce que le membre doit pouvoir refaire seul à la fin.",
        inline=False,
    )
    e.add_field(
        name="Quand escalader",
        value="Paiement, permission dangereuse, incident sécurité, conflit staff ou demande hors compétence → Direction / Responsable avant toute action sensible.",
        inline=False,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V44 • Cockpit staff • responsabilité claire • actions sensibles contrôlées")
    return e


def _rules_embed_v44(self: SetupServerCog) -> discord.Embed:
    e = discord.Embed(
        title="Règlement — Aide Bot",
        description=(
            "**Respect** — pas d’insultes, harcèlement, spam ou contenu nuisible.\n"
            "**Sécurité** — jamais de token, mot de passe, cookie, code 2FA, code de récupération ou donnée bancaire.\n"
            "**Support** — une demande précise par ticket ; utilise le diagnostic avant d’ouvrir un salon.\n"
            "**Premium** — achat uniquement dans `🛒・shop` ou via `/buy`; la validation enregistrée par la Direction fait foi.\n"
            "**Staff** — évite les pings multiples ; le responsable assigné suit la demande ou l’escalade proprement.\n"
            "**Formation** — le but est de comprendre, pratiquer et pouvoir refaire seul, pas de copier une réponse sans explication."
        ),
        color=0x2B2D31,
    )
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V44 • Respect • sécurité • demandes claires • apprentissage réel")
    return e


def _quality_snapshot(guild: discord.Guild) -> tuple[int, int, int, list[str]]:
    expected_roles = [name for name, _color, _perms in ROLE_SPECS]
    expected_categories = [name for name, _channels in CATEGORY_SPECS]
    expected_channels = [channel for _category, channels in CATEGORY_SPECS for channel in channels]
    role_ok = sum(1 for name in expected_roles if discord.utils.get(guild.roles, name=name))
    category_ok = sum(1 for name in expected_categories if discord.utils.get(guild.categories, name=name))
    channel_ok = sum(1 for name in expected_channels if discord.utils.get(guild.text_channels, name=name))
    missing: list[str] = []
    missing.extend(name for name in expected_roles if not discord.utils.get(guild.roles, name=name))
    missing.extend(name for name in expected_categories if not discord.utils.get(guild.categories, name=name))
    missing.extend(name for name in expected_channels if not discord.utils.get(guild.text_channels, name=name))
    return role_ok, category_ok, channel_ok, missing


def _setup_success_embed(guild: discord.Guild) -> discord.Embed:
    role_ok, category_ok, channel_ok, missing = _quality_snapshot(guild)
    expected_roles = len(ROLE_SPECS)
    expected_categories = len(CATEGORY_SPECS)
    expected_channels = sum(len(channels) for _category, channels in CATEGORY_SPECS)
    total = expected_roles + expected_categories + expected_channels
    current = role_ok + category_ok + channel_ok
    score = round((current / total) * 100) if total else 100
    e = discord.Embed(
        title=f"Aide Bot V44 — setup terminé • {score}%",
        description=(
            "Le setup a réconcilié l’architecture Aide Bot et les panneaux principaux. Cette carte vérifie aussi que les objets canoniques attendus existent réellement après l’opération."
        ),
        color=0x57F287 if not missing else 0xF1C40F,
    )
    e.add_field(name="Rôles", value=f"**{role_ok}/{expected_roles}** présents", inline=True)
    e.add_field(name="Catégories", value=f"**{category_ok}/{expected_categories}** présentes", inline=True)
    e.add_field(name="Salons", value=f"**{channel_ok}/{expected_channels}** présents", inline=True)
    e.add_field(
        name="Parcours membre",
        value="`👋・bienvenue` → `🎓・centre-aide` → guides/formations/vidéos/support → `🛒・shop` seulement si Premium",
        inline=False,
    )
    e.add_field(
        name="Tests recommandés",
        value=(
            "**1.** Centre → Support intelligent → Bot/code → checklist → formulaire.\n"
            "**2.** Formations → ouvrir deux parcours et comparer programme + ressources.\n"
            "**3.** Boutique → tester Free/Premium et le statut VIP.\n"
            "**4.** Recrutement → envoyer une candidature test puis la traiter côté staff.\n"
            "**5.** Ouvrir un vrai ticket, le prendre, avancer, terminer puis archiver."
        ),
        inline=False,
    )
    if missing:
        e.add_field(name="À corriger", value="\n".join(f"• {item}" for item in missing[:12]), inline=False)
    else:
        e.add_field(name="Contrôle structure", value="Tous les rôles, catégories et salons canoniques attendus sont présents.", inline=False)
    e.set_image(url=BANNER_URL)
    e.set_footer(text="Aide Bot V44 • /setup est idempotent : relance-le pour réparer ou mettre à jour les panneaux")
    return e


class SetupPolishV43Cog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        SetupServerCog._training_embed = _training_embed_v44
        SetupServerCog._staff_embed = _staff_embed_v44
        SetupServerCog._rules_embed = _rules_embed_v44

        command = SetupServerCog.setup_server
        if getattr(command, "_aidebot_v44_wrapped", False):
            return
        original = command.callback

        async def callback(cog: SetupServerCog, interaction: discord.Interaction) -> None:
            await original(cog, interaction)
            if not interaction.guild or not isinstance(interaction.user, discord.Member):
                return
            guild = interaction.guild
            me = guild.me
            if me is None:
                return
            allowed_user = guild.owner_id == interaction.user.id or interaction.user.guild_permissions.administrator
            required_ok = all((
                me.guild_permissions.manage_roles,
                me.guild_permissions.manage_channels,
                me.guild_permissions.view_channel,
                me.guild_permissions.send_messages,
                me.guild_permissions.embed_links,
                me.guild_permissions.read_message_history,
            ))
            collisions = canonical_collisions(
                role_names=(role.name for role in guild.roles),
                category_names=(category.name for category in guild.categories),
                channel_names=(channel.name for channel in guild.text_channels),
            )
            if not allowed_user or not required_ok or collisions:
                return
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(embed=_setup_success_embed(guild), ephemeral=True)
            except (discord.HTTPException, discord.NotFound):
                pass

        command.callback = callback
        command._aidebot_v44_wrapped = True


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SetupPolishV43Cog(bot))
