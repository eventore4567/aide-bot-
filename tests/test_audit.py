from aidebot.audit import dangerous_permissions, format_permission_names


class Perms:
    administrator = False
    manage_guild = True
    manage_roles = True
    manage_channels = False
    ban_members = False
    kick_members = False
    moderate_members = True
    manage_webhooks = False


def test_dangerous_permissions_detects_only_enabled_flags():
    found = dangerous_permissions(Perms())
    assert found == ["manage_guild", "manage_roles", "moderate_members"]


def test_permission_labels_are_human_readable():
    text = format_permission_names(["manage_roles", "moderate_members"])
    assert "Gérer les rôles" in text
    assert "Exclure temporairement des membres" in text
