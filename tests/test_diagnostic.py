from aidebot.diagnostic import diagnose, recommended_commands


def test_routes_bot_problem_to_bot_learning():
    result = diagnose("Je veux créer un bot Discord avec Python et une commande slash")
    assert result.route.key == "bot"
    assert result.route.learning_path == "bot"
    assert result.confidence in {"moyenne", "élevée"}


def test_routes_permissions_problem_to_security_path():
    result = diagnose("Mes permissions et rôles sont mal configurés, mon salon staff privé est visible")
    assert result.route.key == "permissions"
    assert result.route.resource_key == "permissions"
    assert result.route.challenge_key == "permissions-1"


def test_routes_ticket_problem_to_support():
    result = diagnose("Je veux organiser les tickets support entre Helpers, Formateurs et staff")
    assert result.route.key == "support"
    assert result.route.resource_key == "tickets"


def test_unknown_problem_falls_back_without_fake_confidence():
    result = diagnose("je suis perdu et je ne sais pas quoi faire")
    assert result.route.key == "discord"
    assert result.confidence == "faible"
    assert result.score == 0


def test_compromised_token_prioritizes_security():
    result = diagnose("Mon token est exposé et mon bot est compromis")
    assert result.urgent_security is True
    assert result.route.key == "permissions"
    assert result.confidence == "élevée"


def test_recommendations_include_free_and_human_paths():
    result = diagnose("Je veux apprendre les permissions Discord")
    commands = recommended_commands(result)
    text = "\n".join(commands)
    assert "/apprendre" in text
    assert "/chercher" in text
    assert "/aide demander" in text
    assert "/parcours" in text
