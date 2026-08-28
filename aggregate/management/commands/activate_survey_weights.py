from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import re

from aggregate.models import SurveyWeightSet
from aggregate.weighting import canonical_respondent_key, fingerprint_dataset
from surnasdes26.services.dataset import DatasetUnavailable, get_dataset
from surnasdes26.services.registry import SurveyRegistryError, get_survey


class Command(BaseCommand):
    help = "Mengaktifkan satu versi bobot setelah memeriksa ulang dataset terbaru."

    def add_arguments(self, parser):
        parser.add_argument("--survey-code", required=True)
        parser.add_argument("--weight-version", required=True)

    def handle(self, *args, **options):
        survey_code = options["survey_code"].strip().lower()
        version = options["weight_version"].strip().lower()
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,79}", version):
            raise CommandError("Weight version tidak valid.")
        try:
            weight_set = SurveyWeightSet.objects.select_related("survey").get(
                survey__code=survey_code,
                version=version,
            )
            manifest = get_survey(survey_code)
            dataset = get_dataset(force_refresh=True, survey_code=survey_code)
        except SurveyWeightSet.DoesNotExist as exc:
            raise CommandError("Versi bobot tidak ditemukan.") from exc
        except (SurveyRegistryError, DatasetUnavailable) as exc:
            raise CommandError(str(exc)) from exc

        key_column = weight_set.key_column.upper()
        if key_column not in dataset.columns:
            raise CommandError(f"Kolom key dataset tidak tersedia: {key_column}.")
        dataset_keys = {
            canonical_respondent_key(value)
            for value in dataset[key_column]
            if canonical_respondent_key(value)
        }
        weight_keys = set(weight_set.weights.values_list("respondent_key", flat=True))
        missing_count = len(dataset_keys - weight_keys)
        unknown_count = len(weight_keys - dataset_keys)
        fingerprint_match = fingerprint_dataset(
            dataset,
            key_column,
            manifest["dataset"].get("latest_id_column"),
        ) == weight_set.dataset_fingerprint
        if missing_count or unknown_count or not fingerprint_match:
            raise CommandError(
                "Versi bobot tidak sinkron dengan dataset terbaru: "
                f"missing={missing_count}, unknown={unknown_count}, "
                f"fingerprint_match={fingerprint_match}."
            )
        if manifest["dataset"]["identity_column"] != key_column:
            raise CommandError("Key bobot tidak sama dengan identity_column registry.")

        with transaction.atomic():
            SurveyWeightSet.objects.filter(survey=weight_set.survey, is_active=True).update(
                is_active=False
            )
            weight_set.is_active = True
            weight_set.save(update_fields=["is_active"])
        self.stdout.write(self.style.SUCCESS("Aktivasi bobot: OK"))
        self.stdout.write(f"Survey code: {survey_code}")
        self.stdout.write(f"Version aktif: {version}")
        self.stdout.write(f"Kasus: {len(dataset_keys)}")
        self.stdout.write("Coverage: 100.0000%")
