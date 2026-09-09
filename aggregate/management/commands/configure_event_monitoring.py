from copy import deepcopy

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from aggregate.event_validation import event_configuration_signature
from aggregate.models import SurveyAccess
from aggregate.module_readiness import refresh_event_module_readiness


class Command(BaseCommand):
    help = "Mengonfigurasi variabel pengelompokan monitoring event secara tervalidasi."

    def add_arguments(self, parser):
        parser.add_argument("--survey", required=True)
        parser.add_argument("--variable", required=True)
        parser.add_argument("--label")
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        code = options["survey"].strip().lower()
        variable = options["variable"].strip().upper()
        try:
            survey = SurveyAccess.objects.select_related("data_source").get(code=code)
        except SurveyAccess.DoesNotExist as exc:
            raise CommandError("Event tidak ditemukan.") from exc
        metadata_rows = list(survey.metadata_versions.filter(is_active=True)[:2])
        if len(metadata_rows) != 1:
            raise CommandError("Event harus memiliki tepat satu metadata aktif.")
        metadata = metadata_rows[0]
        variables = {
            str(name).strip().upper(): definition
            for name, definition in metadata.payload.get("variables", {}).items()
        }
        if variable not in variables:
            raise CommandError(f"Variabel {variable} tidak tersedia pada metadata aktif.")
        definition = variables[variable]
        default_label = definition.get("label", variable) if isinstance(definition, dict) else variable
        label = (options.get("label") or default_label).strip()
        if not label:
            raise CommandError("Label monitoring tidak boleh kosong.")

        self.stdout.write(
            "Konfigurasi monitoring: APPLY" if options["apply"] else "Konfigurasi monitoring: PREVIEW"
        )
        self.stdout.write(f"Survey code: {survey.code}")
        self.stdout.write(f"Current active: {str(survey.active).lower()}")
        self.stdout.write(f"Variable: {variable}")
        self.stdout.write(f"Label: {label}")
        self.stdout.write("Variable in metadata: true")
        if not options["apply"]:
            self.stdout.write("Preview selesai; konfigurasi belum diubah.")
            return

        with transaction.atomic():
            locked = SurveyAccess.objects.select_for_update().select_related("data_source").get(
                pk=survey.pk
            )
            locked_metadata = locked.metadata_versions.select_for_update().get(pk=metadata.pk)
            previous_signature = locked.validation_report.get("configuration_signature", "")
            dashboard = deepcopy(locked.dashboard_config or {})
            dashboard.update(
                monitoring_group_variable=variable,
                monitoring_group_label=label,
            )
            locked.dashboard_config = dashboard
            update_fields = ["dashboard_config"]
            if locked.active and locked.validation_state == SurveyAccess.ValidationState.PASSED:
                report = deepcopy(locked.validation_report)
                history = list(report.get("configuration_signature_history", []))
                if previous_signature:
                    history.append(
                        {
                            "changed_at": timezone.now().isoformat(),
                            "previous": previous_signature,
                            "reason": "monitoring_configuration",
                        }
                    )
                report["configuration_signature_history"] = history[-10:]
                report["configuration_signature"] = event_configuration_signature(
                    locked, locked.data_source, locked_metadata
                )
                locked.validation_report = report
                update_fields.append("validation_report")
            else:
                locked.validation_state = SurveyAccess.ValidationState.NOT_RUN
                locked.validated_at = None
                locked.validation_fingerprint = ""
                locked.validation_report = {}
                update_fields.extend(
                    [
                        "validation_state",
                        "validated_at",
                        "validation_fingerprint",
                        "validation_report",
                    ]
                )
            locked.save(update_fields=tuple(update_fields))

        survey.refresh_from_db()
        refresh_event_module_readiness(survey)
        self.stdout.write(self.style.SUCCESS("Konfigurasi monitoring: APPLIED"))
        self.stdout.write(f"Event tetap aktif: {str(survey.active).lower()}")
        self.stdout.write("Read-only reporting database: tidak diubah")
