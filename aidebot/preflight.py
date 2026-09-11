from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


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


async def _scalar(conn: Any, sql: str) -> int:
    cur = await conn.execute(sql)
    row = await cur.fetchone()
    if row is None:
        return 0
    try:
        return int(row[0])
    except (KeyError, TypeError):
        return int(next(iter(row)))


async def database_integrity_counts(conn: Any) -> dict[str, int]:
    """Read-only consistency checks used before a production launch.

    The checks intentionally do not repair anything. A preflight audit must be
    safe to run repeatedly and must never mutate production data.
    """
    queries = {
        "duplicate_active_requests": """
            SELECT COUNT(*) FROM (
                SELECT guild_id,user_id,training_key
                FROM requests
                WHERE status IN ('open','assigned','in_progress','payment_pending')
                GROUP BY guild_id,user_id,training_key
                HAVING COUNT(*) > 1
            )
        """,
        "active_without_channel": """
            SELECT COUNT(*) FROM requests
            WHERE status IN ('open','assigned','in_progress','payment_pending')
              AND channel_id IS NULL
        """,
        "assigned_without_trainer": """
            SELECT COUNT(*) FROM requests
            WHERE status IN ('assigned','in_progress') AND trainer_id IS NULL
        """,
        "invalid_progress": """
            SELECT COUNT(*) FROM requests
            WHERE total_steps < 1 OR progress < 0 OR progress > total_steps
        """,
        "payment_status_mismatch": """
            SELECT COUNT(*) FROM requests
            WHERE (payment_status='pending' AND status!='payment_pending')
               OR (payment_status='refused' AND status!='payment_refused')
               OR (payment_status='refunded' AND status NOT IN ('payment_refunded','completed','closed'))
               OR (payment_status='paid' AND status IN ('payment_pending','payment_refused'))
               OR (payment_status='not_required' AND status IN ('payment_pending','payment_refused','payment_refunded'))
               OR payment_status NOT IN ('not_required','pending','paid','refused','refunded')
        """,
        "negative_invite_credits": """
            SELECT COUNT(*) FROM invite_credits WHERE credits < 0
        """,
        "invalid_reviews": """
            SELECT COUNT(*) FROM reviews WHERE rating < 1 OR rating > 5
        """,
        "terminal_pending_reminders": """
            SELECT COUNT(*)
            FROM reminders r
            JOIN requests q ON q.id=r.request_id
            WHERE r.state='pending'
              AND q.status IN ('completed','closed','cancelled','payment_refunded')
        """,
        "invalid_applications": """
            SELECT COUNT(*) FROM applications
            WHERE target_role NOT IN ('helper','trainer')
               OR status NOT IN ('pending','accepted','rejected')
        """,
        "invalid_learning_progress": """
            SELECT COUNT(*) FROM learning_progress
            WHERE max_lesson < 0 OR quiz_attempts < 0 OR quiz_correct < 0 OR quiz_correct > quiz_attempts
        """,
    }
    return {key: await _scalar(conn, sql) for key, sql in queries.items()}
