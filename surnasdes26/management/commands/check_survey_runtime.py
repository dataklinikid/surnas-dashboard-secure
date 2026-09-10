from django.core.management.base import BaseCommand, CommandError

from aggregate.models import SurveyAccess
from surnasdes26.services.registry import SurveyRegistryError
from surnasdes26.services.runtime import resolve_survey


class Command(BaseCommand):
    help = "Memeriksa sumber konfigurasi runtime satu event tanpa membaca data responden."

    def add_arguments(self, parser):
        parser.add_argument("--survey", required=True)
        parser.add_argument("--require-postgresql", action="store_true")

    def handle(self, *args, **options):
        code = options["survey"].strip().lower()
        try:
            manifest = resolve_survey(code)
            survey = SurveyAccess.objects.get(code=code)
        except (SurveyRegistryError, SurveyAccess.DoesNotExist) as exc:
            raise CommandError(str(exc)) from exc

        source = manifest["configuration_source"]
        if options["require_postgresql"] and source != "postgresql":
            raise CommandError("Runtime masih menggunakan fallback JSON.")

        self.stdout.write("Runtime survey configuration: OK")
        self.stdout.write(f"Survey code: {manifest['code']}")
        self.stdout.write(f"Configuration source: {source}")
        self.stdout.write(f"Program: {(manifest.get('program') or {}).get('code', '-')}")
        self.stdout.write(f"Region: {(manifest.get('region') or {}).get('code', '-')}")
        self.stdout.write(f"Database alias: {manifest['database']['alias']}")
        self.stdout.write(f"Table: {manifest['database']['table']}")
        self.stdout.write(f"Identity: {manifest['dataset']['identity_column']}")
        self.stdout.write(f"Latest ID: {manifest['dataset']['latest_id_column'] or '-'}")
        self.stdout.write(f"Metadata version: {manifest['metadata'].get('version', 'JSON legacy')}")
        self.stdout.write(f"Metadata variables: {len(manifest['metadata'].get('payload', {}).get('variables', {})) if source == 'postgresql' else '-'}")
        self.stdout.write(f"Memberships: {survey.memberships.count()}")
        self.stdout.write(f"Weight sets: {survey.weight_sets.count()}")
        self.stdout.write(f"Active weights: {survey.weight_sets.filter(is_active=True).count()}")
