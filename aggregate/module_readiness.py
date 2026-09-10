from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist

from aggregate.models import SurveyAccess, SurveyEventModule


READY_AFTER_DATASET_VALIDATION = {
    "survey_analytics": "Dataset final dan metadata telah lulus validasi.",
}

PENDING_REASONS = {
    "fieldwork_monitoring": "Variabel pengelompokan monitoring belum dikonfigurasi.",
    "weighted_analysis": "Belum ada weight set aktif yang cocok dengan fingerprint dataset.",
    "sampling_frame": "Master sampling frame dan PSU belum tersedia.",
    "reporting": "Semantic mapping dan report template belum dikonfigurasi.",
    "quick_count": "Master TPS/DPT dan konfigurasi quick count belum tersedia.",
    "personnel_monitoring": "Master personel dan penugasan belum tersedia.",
}


def _fieldwork_monitoring_ready(survey):
    active_frames = list(survey.psu_frames.filter(is_active=True)[:2])
    if active_frames:
        try:
            config = survey.monitoring_config
        except ObjectDoesNotExist:
            return False
        return bool(config.questionnaire_column)
    variable = str(
        (survey.dashboard_config or {}).get("monitoring_group_variable", "")
    ).strip().upper()
    metadata_rows = list(survey.metadata_versions.filter(is_active=True)[:2])
    if not variable or len(metadata_rows) != 1:
        return False
    variables = {
        str(name).strip().upper()
        for name in metadata_rows[0].payload.get("variables", {})
    }
    return variable in variables


def _sampling_frame_ready(survey):
    frames = list(survey.psu_frames.filter(is_active=True)[:2])
    return (
        len(frames) == 1
        and frames[0].row_count > 0
        and frames[0].target_total > 0
        and frames[0].psus.count() == frames[0].row_count
    )


def _weighted_analysis_ready(survey):
    rows = list(survey.weight_sets.filter(is_active=True)[:2])
    if len(rows) != 1:
        return False
    weight_set = rows[0]
    fingerprint = survey.validation_report.get("dataset_fingerprint", "")
    return (
        weight_set.coverage == Decimal("100.0000")
        and bool(fingerprint)
        and weight_set.dataset_fingerprint == fingerprint
    )


def desired_module_state(survey, module_code):
    if survey.validation_state == SurveyAccess.ValidationState.FAILED:
        return SurveyEventModule.Readiness.BLOCKED, "Validasi dataset masih gagal."
    if survey.validation_state != SurveyAccess.ValidationState.PASSED:
        return SurveyEventModule.Readiness.PENDING, "Validasi final belum dijalankan."
    if module_code in READY_AFTER_DATASET_VALIDATION:
        return SurveyEventModule.Readiness.READY, READY_AFTER_DATASET_VALIDATION[module_code]
    if module_code == "fieldwork_monitoring" and _fieldwork_monitoring_ready(survey):
        return (
            SurveyEventModule.Readiness.READY,
            "Dataset final, metadata, dan variabel monitoring telah dikonfigurasi.",
        )
    if module_code == "sampling_frame" and _sampling_frame_ready(survey):
        return SurveyEventModule.Readiness.READY, "Frame PSU aktif dan lolos pemeriksaan integritas."
    if module_code == "weighted_analysis" and _weighted_analysis_ready(survey):
        return SurveyEventModule.Readiness.READY, "Weight set aktif cocok dengan fingerprint dataset."
    return (
        SurveyEventModule.Readiness.PENDING,
        PENDING_REASONS.get(module_code, "Konfigurasi modul belum lengkap."),
    )


def refresh_event_module_readiness(survey):
    for assignment in survey.event_modules.select_related("module"):
        desired, _reason = desired_module_state(survey, assignment.module.code)
        if assignment.readiness != desired:
            assignment.readiness = desired
            assignment.save(update_fields=("readiness", "updated_at"))


def event_module_readiness_rows(survey):
    rows = []
    for assignment in survey.event_modules.select_related("module").order_by(
        "module__display_order", "module__name"
    ):
        _desired, reason = desired_module_state(survey, assignment.module.code)
        rows.append(
            {
                "name": assignment.module.name,
                "code": assignment.module.code,
                "enabled": assignment.enabled,
                "readiness": assignment.readiness,
                "readiness_label": assignment.get_readiness_display(),
                "reason": reason,
            }
        )
    return rows
