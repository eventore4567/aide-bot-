from aidebot.health import missing_permission_labels, persistence_check


class Permissions:
    manage_roles = True
    manage_channels = True
    manage_guild = False
    send_messages = True
    embed_links = True


def test_railway_sqlite_warns_without_persistent_path():
    result = persistence_check("data/aidebot.db", railway=True)
    assert result.ok is False
    assert "redéploiement" in result.message


def test_railway_sqlite_accepts_data_volume_path():
    result = persistence_check("/data/aidebot.db", railway=True)
    assert result.ok is True


def test_local_sqlite_is_valid_for_local_development():
    result = persistence_check("data/aidebot.db", railway=False)
    assert result.ok is True


def test_invite_permission_is_checked():
    missing = missing_permission_labels(Permissions())
    assert missing == ["Gérer le serveur (lecture des invitations)"]
