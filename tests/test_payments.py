from aidebot.payments import PAYMENT_LABELS, REQUEST_STATUS_FOR_PAYMENT, normalize_payment_state


def test_payment_aliases_normalize():
    assert normalize_payment_state("payé") == "paid"
    assert normalize_payment_state("En attente") == "pending"
    assert normalize_payment_state("refusé") == "refused"
    assert normalize_payment_state("remboursé") == "refunded"


def test_invalid_payment_state_is_rejected():
    assert normalize_payment_state("ok") is None


def test_payment_states_map_to_request_statuses():
    assert REQUEST_STATUS_FOR_PAYMENT["paid"] == "open"
    assert REQUEST_STATUS_FOR_PAYMENT["pending"] == "payment_pending"
    assert REQUEST_STATUS_FOR_PAYMENT["refused"] == "payment_refused"
    assert REQUEST_STATUS_FOR_PAYMENT["refunded"] == "payment_refunded"


def test_every_payment_state_has_a_label():
    assert set(PAYMENT_LABELS) == set(REQUEST_STATUS_FOR_PAYMENT)
