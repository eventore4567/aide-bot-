from aidebot.progression import community_level, profile_badges


def test_community_levels_progress_monotonically():
    assert community_level(0) == "Nouveau"
    assert community_level(100) == "Contributeur"
    assert community_level(250) == "Confirmé"
    assert community_level(500) == "Expert"
    assert community_level(1000) == "Pilier"


def test_new_profile_has_default_badge():
    assert profile_badges(reputation=0, helped=0, trainings=0, reviews=0, average=0.0) == ["🌱 Nouveau"]


def test_active_profile_gets_multiple_badges():
    badges = profile_badges(reputation=1000, helped=12, trainings=6, reviews=8, average=4.8)
    assert "🧭 Helper confirmé" in badges
    assert "📘 Formateur actif" in badges
    assert "⭐ Très bien noté" in badges
    assert "💠 Pilier Aide Bot" in badges
