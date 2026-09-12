import asyncio

import discord

from aidebot.cogs.center import CenterView, center_embed
from aidebot.cogs.help_center_v46 import HELP_TOPICS, HelpCenterV46View, HelpTopicSelect, help_topic_embed
from aidebot.cogs import recruitment_panel as legacy_recruitment
from aidebot.cogs.recruitment_v46 import (
    RECRUITMENT_TRACKS,
    RecruitmentV46Cog,
    RecruitmentV46View,
    RoleApplicationModal,
    recruitment_v46_embed,
)


class DummyBot:
    def __init__(self):
        self.views = []

    def add_view(self, view):
        self.views.append(view)


def test_v46_center_has_many_real_help_choices():
    embed = center_embed(500)
    title = (embed.title or "").casefold()
    assert "centre d’aide" in title
    assert "tableau de bord" in title
    text = ((embed.description or "") + "\n" + "\n".join(field.value for field in embed.fields)).casefold()
    assert "vrai centre d’aide" in text
    assert "13 sujets" in text

    view = HelpCenterV46View(object())
    assert view.timeout is None
    selects = [item for item in view.children if isinstance(item, HelpTopicSelect)]
    assert len(selects) == 1
    assert len(selects[0].options) == len(HELP_TOPICS)
    assert len(HELP_TOPICS) >= 13

    labels = {getattr(item, "label", None) for item in view.children}
    assert {"Formations", "Support / Tickets", "Vidéos", "Candidatures", "Premium", "Mon espace"}.issubset(labels)


def test_every_help_topic_has_actionable_content():
    required = {"discord", "server", "permissions", "security", "moderation", "tickets", "bot", "webhooks", "hosting", "database", "github", "premium", "recruitment", "other"}
    assert required.issubset(HELP_TOPICS)

    for key, data in HELP_TOPICS.items():
        assert len(data["steps"]) >= 3
        assert data["covers"]
        assert data["mistakes"]
        embed = help_topic_embed(key)
        names = {field.name for field in embed.fields}
        assert {"Ce que cette aide couvre", "Commence par ça", "Erreurs fréquentes", "Si tu bloques encore"}.issubset(names)
        assert embed.image.url


def test_center_view_is_now_v46_help_center():
    class Cog:
        bot = object()

    view = CenterView(Cog())
    assert isinstance(view, HelpCenterV46View)
    assert view.timeout is None


def test_recruitment_has_four_specific_tracks_and_five_questions_each():
    assert set(RECRUITMENT_TRACKS) == {"helper", "trainer", "bot_expert", "security_expert"}
    prompts = set()
    all_labels = []
    for key, data in RECRUITMENT_TRACKS.items():
        assert len(data["questions"]) == 5
        modal = RoleApplicationModal(object(), key)
        assert len(modal.children) == 5
        labels = tuple(field.label for field in modal.children)
        prompts.add(labels)
        all_labels.extend(labels)
    assert len(prompts) == 4
    assert any("cas pratique" in label.casefold() for label in all_labels)

    embed = recruitment_v46_embed()
    text = ((embed.description or "") + "\n" + "\n".join(field.value for field in embed.fields)).casefold()
    assert "questionnaire" in text

    view = RecruitmentV46View(object())
    assert view.timeout is None
    assert len(view.children) == 1
    assert isinstance(view.children[0], discord.ui.Select)
    assert len(view.children[0].options) == 4


def test_recruitment_v46_extends_atomic_acceptance_role_mapping():
    bot = DummyBot()
    asyncio.run(RecruitmentV46Cog(bot).cog_load())
    assert legacy_recruitment.APPLICATION_ROLE_NAMES["bot_expert"] == "🤖・Expert Bots"
    assert legacy_recruitment.APPLICATION_ROLE_NAMES["security_expert"] == "🛡️・Expert Sécurité"
    assert any(isinstance(view, RecruitmentV46View) for view in bot.views)
