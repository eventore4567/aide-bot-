from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

from aidebot.blueprint import CATEGORY_SPECS, ROLE_SPECS


@dataclass(frozen=True)
class NameCollision:
    kind: str
    name: str
    count: int


CANONICAL_ROLE_NAMES = frozenset(name for name, _, _ in ROLE_SPECS)
CANONICAL_CATEGORY_NAMES = frozenset(name for name, _ in CATEGORY_SPECS)
CANONICAL_CHANNEL_NAMES = frozenset(
    channel_name
    for _, channel_names in CATEGORY_SPECS
    for channel_name in channel_names
)


def _duplicates(names: Iterable[str], canonical: frozenset[str], kind: str) -> list[NameCollision]:
    counts = Counter(name for name in names if name in canonical)
    return [
        NameCollision(kind=kind, name=name, count=count)
        for name, count in sorted(counts.items())
        if count > 1
    ]


def canonical_collisions(
    *,
    role_names: Iterable[str],
    category_names: Iterable[str],
    channel_names: Iterable[str],
) -> list[NameCollision]:
    """Return ambiguous canonical names that make setup unsafe.

    Aide Bot relies on stable canonical role/category/channel names. If two
    Discord objects have the same canonical name, silently picking the first
    object could reconcile permissions on the wrong target. Setup therefore
    fails closed until the duplicate is renamed or removed by the owner.
    """
    return [
        *_duplicates(role_names, CANONICAL_ROLE_NAMES, "rôle"),
        *_duplicates(category_names, CANONICAL_CATEGORY_NAMES, "catégorie"),
        *_duplicates(channel_names, CANONICAL_CHANNEL_NAMES, "salon"),
    ]


def format_collisions(collisions: list[NameCollision], limit: int = 10) -> str:
    lines = [f"• {item.kind} **{item.name}** ×{item.count}" for item in collisions[:limit]]
    if len(collisions) > limit:
        lines.append(f"• … et {len(collisions) - limit} autre(s) collision(s)")
    return "\n".join(lines)
