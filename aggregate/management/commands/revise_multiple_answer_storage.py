import hashlib
import json
from copy import deepcopy

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from aggregate.event_validation import event_configuration_signature
from aggregate.models import SurveyAccess, SurveyMetadataVersion
from aggregate.module_readiness import refresh_event_module_readiness
from aggregate.multiple_answer_revision import revise_compact_groups
from surnasdes26.services.dataset import get_dataset
from surnasdes26.services.runtime import metadata_sha256
from surnasdes26.services.tabulation import canonical_code


class Command(BaseCommand):
    help = "Merevisi grup multiple-answer ke penyimpanan compact_codes secara terversi."

    def add_arguments(self, parser):
        parser.add_argument("--survey", required=True)
        parser.add_argument("--groups", nargs="+", required=True)
        parser.add_argument(
            "--metadata-version",
            dest="metadata_version",
            default="metadata_v2",
        )
        parser.add_argument(
            "--eligibility",
            choices=("all_respondents", "source_not_blank"),
            required=True,
        )
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        code = options["survey"].strip().lower()
        names = [name.strip().upper() for name in options["groups"]]
        version = options["metadata_version"].strip().lower()
        eligibility = options["eligibility"]
        try:
            survey = SurveyAccess.objects.select_related("data_source").get(code=code)
        except SurveyAccess.DoesNotExist as exc:
            raise CommandError("Event tidak ditemukan.") from exc
        metadata_rows = list(survey.metadata_versions.filter(is_active=True)[:2])
        if len(metadata_rows) != 1:
            raise CommandError("Event harus memiliki tepat satu metadata aktif.")
        if survey.metadata_versions.filter(version=version).exists():
            raise CommandError(f"Versi metadata {version} sudah digunakan.")
        if not survey.active or survey.validation_state != SurveyAccess.ValidationState.PASSED:
            raise CommandError("Revisi ini memerlukan event aktif dengan validation_state passed.")

        old_metadata = metadata_rows[0]
        try:
            payload = revise_compact_groups(old_metadata.payload, names, eligibility)
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        frame = get_dataset(force_refresh=True, survey_code=survey.code)
        audit = []
        for name in names:
            if name not in frame.columns:
                raise CommandError(f"Kolom sumber {name} tidak tersedia pada dataset final.")
            values = frame[name].map(canonical_code)
            allowed = {
                str(option["source_code"])
                for option in payload["multiple_answer_groups"][name]["options"]
            }
            invalid = sorted(
                {
                    character
                    for value in values
                    for character in value
                    if character not in allowed
                }
            )
            if invalid:
                raise CommandError(
                    f"Kolom {name} memiliki kode di luar metadata: {', '.join(invalid)}."
                )
            audit.append(
                (
                    name,
                    int(values.ne("").sum()),
                    sum(len(value) for value in values),
                )
            )

        new_sha = metadata_sha256(payload)
        self.stdout.write(
            "Revisi multiple-answer: APPLY" if options["apply"] else "Revisi multiple-answer: PREVIEW"
        )
        self.stdout.write(f"Survey code: {survey.code}")
        self.stdout.write(f"Metadata lama: {old_metadata.version}")
        self.stdout.write(f"Metadata baru: {version}")
        self.stdout.write(f"Eligibility: {eligibility}")
        for name, nonblank, selections in audit:
            self.stdout.write(
                f"Group {name}: source={name}; nonblank={nonblank}; selections={selections}"
            )
        self.stdout.write(f"New metadata SHA256: {new_sha}")
        self.stdout.write("Reporting database writes: 0")
        if not options["apply"]:
            self.stdout.write("Preview selesai; metadata belum diubah.")
            return

        with transaction.atomic():
            locked = SurveyAccess.objects.select_for_update().select_related("data_source").get(
                pk=survey.pk
            )
            locked_old = locked.metadata_versions.select_for_update().get(pk=old_metadata.pk)
            if not locked_old.is_active:
                raise CommandError("Metadata aktif berubah selama revisi.")
            locked_old.is_active = False
            locked_old.save(update_fields=("is_active",))
            new_metadata = SurveyMetadataVersion.objects.create(
                survey=locked,
                version=version,
                metadata_schema_version=locked_old.metadata_schema_version,
                questionnaire_key=locked_old.questionnaire_key,
                source_database=locked_old.source_database,
                payload=payload,
                sha256=new_sha,
                source_name=f"revision:compact_codes:{locked_old.version}",
                onboarding_report=deepcopy(locked_old.onboarding_report),
                is_active=True,
                created_by=locked_old.created_by,
            )

            report = deepcopy(locked.validation_report)
            history = list(report.get("configuration_signature_history", []))
            previous_signature = report.get("configuration_signature", "")
            if previous_signature:
                history.append(
                    {
                        "previous": previous_signature,
                        "reason": "multiple_answer_compact_codes_revision",
                        "metadata_version": locked_old.version,
                    }
                )
            report["configuration_signature_history"] = history[-10:]
            report["metadata_version"] = new_metadata.version
            report["metadata_sha256"] = new_metadata.sha256
            report["configuration_signature"] = event_configuration_signature(
                locked,
                locked.data_source,
                new_metadata,
            )
            locked.validation_report = report
            locked.validation_fingerprint = hashlib.sha256(
                json.dumps(report, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            locked.save(update_fields=("validation_report", "validation_fingerprint"))

        survey.refresh_from_db()
        refresh_event_module_readiness(survey)
        self.stdout.write(self.style.SUCCESS("Revisi multiple-answer: APPLIED"))
        self.stdout.write(f"Event tetap aktif: {str(survey.active).lower()}")
        self.stdout.write(f"Metadata aktif: {version}")
