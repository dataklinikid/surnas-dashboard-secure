from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from surnasdes26.services.legacy_db import count_h0, get_database_config
from surnasdes26.services.registry import get_survey


class Command(BaseCommand):
    help = "Memeriksa koneksi read-only ke database reporting berdasarkan Survey Registry."

    def add_arguments(self, parser):
        parser.add_argument("--survey", help="Survey code; default ACTIVE_SURVEY_CODE.")

    def handle(self, *args, **options):
        if settings.SURNAS_DEMO_MODE:
            self.stdout.write(self.style.WARNING("Mode demo aktif; koneksi MariaDB tidak diperiksa."))
            return
        try:
            survey = get_survey(options.get("survey"))
            config = get_database_config(survey["code"])
            count = count_h0(survey["code"])
        except Exception as exc:
            raise CommandError(
                f"Database reporting tidak dapat dibaca ({exc.__class__.__name__}: {exc})."
            ) from exc
        self.stdout.write(self.style.SUCCESS("Database reporting: OK"))
        self.stdout.write(f"Survey code: {survey['code']}")
        self.stdout.write(f"Database: {config['NAME']}")
        self.stdout.write(f"Host: {config['HOST']}:{config['PORT']}")
        self.stdout.write(f"Tabel: {config['TABLE']}")
        self.stdout.write(f"Baris mentah: {count}")
