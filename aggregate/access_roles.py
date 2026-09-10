ROLE_CAPABILITIES = {
    "monitor": {
        "can_monitor": True,
        "can_analyse": False,
        "can_export": False,
    },
    "analyst": {
        "can_monitor": True,
        "can_analyse": True,
        "can_export": False,
    },
    "admin": {
        "can_monitor": True,
        "can_analyse": True,
        "can_export": True,
    },
}

ROLE_CHOICES = (
    ("monitor", "Monitor — monitoring saja"),
    ("analyst", "Analyst — monitoring dan analisis"),
    ("admin", "Admin event — monitoring, analisis, dan export"),
)


def role_for_capabilities(membership):
    if membership.can_export:
        return "Admin event"
    if membership.can_analyse:
        return "Analyst"
    if membership.can_monitor:
        return "Monitor"
    return "Tanpa hak"
