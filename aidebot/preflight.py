from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class PreflightIssue:
    key: str
    label: str
    count: int
    blocking: bool = True


@dataclass(frozen=True)
class PreflightSummary:
    ready: bool
    blocking_count: int
    warning_count: int


INTEGRITY_LABELS: dict[str, tuple[str, bool]] = {
    "duplicate_active_requests": ("demandes actives dupliquées", True),
    "active_without_channel": ("demandes actives sans salon Discord", True),
    "assigned_without_trainer": ("demandes attribuées sans Formateur/Helper", True),
    "invalid_progress": ("progressions de formation incohérentes", True),
    "payment_status_mismatch": ("états de paiement incohérents", True),
    "negative_invite_credits": ("crédits d'invitation négatifs", True),
    "invalid_reviews": ("avis avec une note hors 1–5", True),
    "terminal_pending_reminders": ("rappels encore actifs sur des demandes terminées", False),
    "invalid_applications": ("candidatures avec un état/type invalide", True),
    "invalid_learning_progress": ("progressions d'apprentissage invalides", True),
}


def classify_integrity(counts: Mapping[str, int]) -> list[PreflightIssue]:
    issues: list[PreflightIssue] = []
    for key, (label, blocking) in INTEGRITY_LABELS.items():
        count = max(0, int(counts.get(key, 0)))
        if count:
            issues.append(PreflightIssue(key=key, label=label, count=count, blocking=blocking))
    return issues


def summarize_preflight(*, hard_blockers: int, integrity_counts: Mapping[str, int], warnings: int = 0) -> PreflightSummary:
    issues = classify_integrity(integrity_counts)
    blocking = max(0, int(hard_blockers)) + sum(issue.count for issue in issues if issue.blocking)
    warning_count = max(0, int(warnings)) + sum(issue.count for issue in issues if not issue.blocking)
    return PreflightSummary(ready=blocking == 0, blocking_count=blocking, warning_count=warning_count)


def format_integrity_issues(counts: Mapping[str, int]) -> list[str]:
    lines: list[str] = []
    for issue in classify_integrity(counts):
        icon = "❌" if issue.blocking else "⚠️"
        lines.append(f"{icon} **{issue.count}** {issue.label}.")
    if not lines:
        lines.append("✅ Aucun défaut d'intégrité connu détecté dans la base.")
    return lines
