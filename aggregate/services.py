from dataclasses import dataclass

from aggregate.models import SurveyAccess, SurveyMembership
from surnasdes26.services.registry import enabled_surveys


@dataclass(frozen=True)
class SurveyCapabilities:
    can_monitor: bool = False
    can_analyse: bool = False
    can_export: bool = False

    @property
    def any_access(self) -> bool:
        return self.can_monitor or self.can_analyse or self.can_export


def capabilities_for(user, survey_code: str) -> SurveyCapabilities:
    if not user.is_authenticated:
        return SurveyCapabilities()
    if user.is_superuser:
        return SurveyCapabilities(True, True, True)

    membership = (
        SurveyMembership.objects.filter(
            user=user,
            survey__code=survey_code,
            survey__active=True,
        )
        .only("can_monitor", "can_analyse", "can_export")
        .first()
    )
    if membership:
        return SurveyCapabilities(
            membership.can_monitor,
            membership.can_analyse,
            membership.can_export,
        )

    if survey_code == "surnasfeb26":
        can_export = user.has_perm("aggregate.export_surnasdes26")
        can_analyse = can_export or user.has_perm("aggregate.access_surnasdes26_analysis")
        can_monitor = can_analyse or user.has_perm("aggregate.access_surnasdes26_monitoring")
        return SurveyCapabilities(can_monitor, can_analyse, can_export)
    return SurveyCapabilities()


def visible_surveys_for(user) -> list[dict]:
    rows = []
    access_rows = {
        row.code: row
        for row in SurveyAccess.objects.filter(active=True)
    }
    for manifest in enabled_surveys():
        if manifest["code"] not in access_rows:
            continue
        capabilities = capabilities_for(user, manifest["code"])
        if not capabilities.any_access:
            continue
        rows.append(
            {
                "code": manifest["code"],
                "name": manifest["name"],
                "can_monitor": capabilities.can_monitor,
                "can_analyse": capabilities.can_analyse,
                "can_export": capabilities.can_export,
            }
        )
    return rows
