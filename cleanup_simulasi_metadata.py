from django.db import transaction
from aggregate.models import SurveyAccess
from aggregate.models import SurveyDataSource
from aggregate.models import SurveyEventModule
from aggregate.models import SurveyMetadataVersion

with transaction.atomic():
    canonical = SurveyAccess.objects.select_for_update().get(
        code="surnasfeb26"
    )
    simulation = SurveyAccess.objects.select_for_update().get(
        code="simulasi_dinamis26"
    )

    if not canonical.active:
        raise RuntimeError(
            "surnasfeb26 tidak aktif; pembersihan dibatalkan."
        )

    rows = list(
        SurveyMetadataVersion.objects
        .filter(survey_id=simulation.pk)
        .values(
            "id",
            "source_name",
            "payload",
            "is_active",
        )
    )

    clone_rows = []

    for row in rows:
        source_name = str(row["source_name"] or "")
        payload = row["payload"]

        if not isinstance(payload, dict):
            continue

        survey_payload = payload.get("survey", {})
        dictionary_name = str(
            survey_payload.get("dictionary_name", "")
        ).strip().upper()

        if (
            source_name.lower().startswith("clone:surnasfeb26:")
            and dictionary_name
            == "SURVEI_NASIONAL_PDAT_FEB26_DICT"
        ):
            clone_rows.append(row)

    if not clone_rows:
        raise RuntimeError(
            "Metadata clone surnasfeb26 tidak ditemukan pada simulasi_dinamis26."
        )

    active_metadata_ids = [
        row["id"]
        for row in clone_rows
        if row["is_active"]
    ]

    metadata_updated = (
        SurveyMetadataVersion.objects
        .filter(id__in=active_metadata_ids)
        .update(is_active=False)
        if active_metadata_ids
        else 0
    )

    source_updated = (
        SurveyDataSource.objects
        .filter(survey_id=simulation.pk, active=True)
        .update(active=False)
    )

    modules_updated = (
        SurveyEventModule.objects
        .filter(survey_id=simulation.pk)
        .update(
            readiness="pending",
            config={},
        )
    )

    simulation.active = False
    simulation.status = SurveyAccess.Status.DRAFT
    simulation.validation_state = (
        SurveyAccess.ValidationState.NOT_RUN
    )
    simulation.validated_at = None
    simulation.validation_fingerprint = ""
    simulation.validation_report = {}
    simulation.dashboard_config = {}

    simulation.save(
        update_fields=(
            "active",
            "status",
            "validation_state",
            "validated_at",
            "validation_fingerprint",
            "validation_report",
            "dashboard_config",
        )
    )

    print("CANONICAL_EVENT=", canonical.code)
    print("SIMULATION_EVENT=", simulation.code)
    print("METADATA_DEACTIVATED=", metadata_updated)
    print("SOURCE_DEACTIVATED=", source_updated)
    print("MODULES_RESET=", modules_updated)
    print("SIMULATION_STATUS=", simulation.status)
    print("SIMULATION_ACTIVE=", simulation.active)
