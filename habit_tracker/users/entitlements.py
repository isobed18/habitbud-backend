from django.utils import timezone


FREE_LIMITS = {
    "habits": 5,
    "proof_submissions_per_day": 5,
    "proof_verifications_per_day": 10,
}

STORE_ITEMS = {
    "streak_freeze": {
        "id": "streak_freeze",
        "name": "Seri Dondurucu",
        "description": "Gunun check-in'i kacarsa seriyi bir kez korur.",
        "price_gems": 20,
        "owned_field": "streak_freezes",
    },
}


def is_paid(user):
    return bool(getattr(user, "is_paid", False))


def get_limits(user):
    if is_paid(user):
        return {
            "habits": None,
            "proof_submissions_per_day": None,
            "proof_verifications_per_day": None,
            "stats_enabled": True,
        }
    return {**FREE_LIMITS, "stats_enabled": False}


def today():
    return timezone.localdate()
