from dataclasses import dataclass

from django.db import transaction
from django.db.models import Q

from aggregate.event_validation import event_configuration_signature
from aggregate.models import (
    SurveyAccess,
    SurveyDataSource,
    SurveyEventModule,
    SurveyMembership,
    SurveyMetadataVersion,
    SurveyWeightSet,
)
from surnasdes26.services.runtime import metadata_sha256


class EventActivationError(ValueError):
    pass


@dataclass(frozen=True)
class ActivationGate:
    errors: tuple[str, ...]
    pending_modules: tuple[str, ...]
    membership_count: int
    configuration_unchanged: bool

    @property
    def passed(self):
        return not self.errors


def evaluate_activation_gate(survey):
    errors = []
    pending_modules = tuple(
        survey.event_modules.filter(enabled=True)
        .exclude(readiness="ready")
        .values_list("module__code", flat=True)
        .order_by("module__code")
    )
    membership_count = survey.memberships.filter(
        Q(can_monitor=True) | Q(can_analyse=True) | Q(can_export=True)
    ).count()
    configuration_unchanged = False

    if survey.status != SurveyAccess.Status.VALIDATION:
        errors.append("Status event harus validation.")
    if survey.active:
        errors.append("Event sudah aktif.")
    if survey.validation_state != SurveyAccess.ValidationState.PASSED:
        errors.append("Validation state harus passed.")
    if survey.validated_at is None or not survey.validation_report:
        errors.append("Laporan validasi tersimpan belum tersedia.")

    try:
        source = survey.data_source
    except SurveyDataSource.DoesNotExist:
        source = None
        errors.append("Data source event tidak ditemukan.")
    metadata_rows = list(survey.metadata_versions.filter(is_active=True)[:2])
    if len(metadata_rows) != 1:
        errors.append("Event harus memiliki tepat satu metadata aktif.")

    if source is not None and len(metadata_rows) == 1:
        metadata = metadata_rows[0]
        if metadata_sha256(metadata.payload) != metadata.sha256:
            errors.append("Checksum metadata berubah setelah validasi.")
        current_signature = event_configuration_signature(survey, source, metadata)
        stored_signature = survey.validation_report.get("configuration_signature", "")
        configuration_unchanged = bool(stored_signature) and current_signature == stored_signature
        if not configuration_unchanged:
            errors.append("Konfigurasi event berubah setelah validasi; validasi ulang diperlukan.")
    if survey.validation_report.get("errors"):
        errors.append("Laporan validasi masih memiliki error.")
    if pending_modules:
        errors.append("Modul belum siap: " + ", ".join(pending_modules) + ".")
    if membership_count == 0:
        errors.append("Minimal satu pengguna operasional harus memiliki akses event.")

    return ActivationGate(
        errors=tuple(errors),
        pending_modules=pending_modules,
        membership_count=membership_count,
        configuration_unchanged=configuration_unchanged,
    )


def activate_event(*, survey):
    with transaction.atomic():
        locked = SurveyAccess.objects.select_for_update().get(pk=survey.pk)
        list(SurveyDataSource.objects.select_for_update().filter(survey=locked))
        list(SurveyMetadataVersion.objects.select_for_update().filter(survey=locked))
        list(SurveyEventModule.objects.select_for_update().filter(survey=locked))
        list(SurveyMembership.objects.select_for_update().filter(survey=locked))
        list(SurveyWeightSet.objects.select_for_update().filter(survey=locked))
        gate = evaluate_activation_gate(locked)
        if not gate.passed:
            raise EventActivationError(" ".join(gate.errors))
        locked.status = SurveyAccess.Status.ACTIVE
        locked.active = True
        locked.save(update_fields=("status", "active"))
    return locked
