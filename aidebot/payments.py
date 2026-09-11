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

# Transitions métier normales. On évite notamment de faire repasser silencieusement
# un paiement déjà payé vers "refusé" ou "en attente".
PAYMENT_TRANSITIONS: dict[str, tuple[str, ...]] = {
    "pending": ("paid", "refused"),
    "refused": ("pending", "paid"),
    "paid": ("refunded",),
    "refunded": ("pending",),
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


def can_transition_payment(current: str, target: str) -> bool:
    if current == target:
        return True
    return target in PAYMENT_TRANSITIONS.get(current, ())


def payment_transition_error(current: str, target: str) -> str:
    current_label = PAYMENT_LABELS.get(current, current)
    target_label = PAYMENT_LABELS.get(target, target)
    allowed = PAYMENT_TRANSITIONS.get(current, ())
    if not allowed:
        return f"Le paiement est actuellement **{current_label}** et aucune transition standard n’est disponible."
    choices = ", ".join(PAYMENT_LABELS.get(item, item) for item in allowed)
    return f"Transition **{current_label} → {target_label}** refusée. Depuis cet état, transitions autorisées : **{choices}**."
