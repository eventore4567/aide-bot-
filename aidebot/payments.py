from __future__ import annotations

PAYMENT_STATES = ("pending", "paid", "refused", "refunded")

REQUEST_STATUS_FOR_PAYMENT = {
    "pending": "payment_pending",
    "paid": "open",
    "refused": "payment_refused",
    "refunded": "payment_refunded",
}

PAYMENT_LABELS = {
    "pending": "En attente",
    "paid": "Payé",
    "refused": "Refusé",
    "refunded": "Remboursé",
}


def normalize_payment_state(value: str) -> str | None:
    normalized = value.casefold().strip()
    aliases = {
        "attente": "pending",
        "en attente": "pending",
        "pending": "pending",
        "paye": "paid",
        "payé": "paid",
        "paid": "paid",
        "refuse": "refused",
        "refusé": "refused",
        "refused": "refused",
        "rembourse": "refunded",
        "remboursé": "refunded",
        "refunded": "refunded",
    }
    return aliases.get(normalized)
