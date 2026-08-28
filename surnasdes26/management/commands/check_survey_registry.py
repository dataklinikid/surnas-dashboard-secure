from django.core.management.base import BaseCommand, CommandError

from surnasdes26.services.metadata import load_metadata
from surnasdes26.services.registry import SurveyRegistryError, enabled_surveys, get_survey


class Command(BaseCommand):
    help = "Memvalidasi Survey Registry dan metadata tanpa membuka database reporting."

    def add_arguments(self, parser):
        parser.add_argument("--survey", help="Survey code; default menggunakan ACTIVE_SURVEY_CODE.")

    def handle(self, *args, **options):
        try:
            survey = get_survey(options.get("survey"))
            metadata = load_metadata(survey["code"])
            surveys = enabled_surveys()
        except (SurveyRegistryError, ValueError, OSError) as exc:
            raise CommandError(str(exc)) from exc

        variables = metadata.get("variables", {})
        self.stdout.write(self.style.SUCCESS("Survey Registry: OK"))
        self.stdout.write(f"Survei aktif: {survey['code']} - {survey['name']}")
        self.stdout.write(f"Survei enabled: {len(surveys)}")
        self.stdout.write(f"Database alias: {survey['database']['alias']}")
        self.stdout.write(f"Tabel sumber: {survey['database']['table']}")
        self.stdout.write(f"Variabel metadata: {len(variables)}")
        self.stdout.write(f"Aggregate only: {bool(survey.get('privacy', {}).get('aggregate_only'))}")
