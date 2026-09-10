from django.core.management.base import BaseCommand, CommandError

from aggregate.event_activation import EventActivationError, activate_event, evaluate_activation_gate
from aggregate.models import SurveyAccess


class Command(BaseCommand):
    help = "Mengaktifkan event yang telah lulus validasi dan belum mengalami perubahan konfigurasi."

    def add_arguments(self, parser):
        parser.add_argument("--survey", required=True)
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        code = options["survey"].strip().lower()
        try:
            survey = SurveyAccess.objects.get(code=code)
        except SurveyAccess.DoesNotExist as exc:
            raise CommandError("Event tidak ditemukan.") from exc
        gate = evaluate_activation_gate(survey)
        self.stdout.write(
            "Aktivasi event: APPLY" if options["apply"] else "Aktivasi event: PREVIEW"
        )
        self.stdout.write(f"Survey code: {survey.code}")
        self.stdout.write(f"Current status: {survey.status}")
        self.stdout.write(f"Current active: {str(survey.active).lower()}")
        self.stdout.write(f"Validation state: {survey.validation_state}")
        self.stdout.write(f"Validated at: {survey.validated_at or '-'}")
        self.stdout.write(f"Configuration unchanged: {str(gate.configuration_unchanged).lower()}")
        self.stdout.write(f"Memberships: {gate.membership_count}")
        self.stdout.write(f"Weight sets: {survey.weight_sets.count()}")
        self.stdout.write(f"Modules not ready: {len(gate.pending_modules)}")
        self.stdout.write(f"Activation errors: {len(gate.errors)}")
        for error in gate.errors:
            self.stdout.write(f"ERROR: {error}")

        if not gate.passed:
            raise CommandError("Activation gate gagal; event tidak diaktifkan.")
        if not options["apply"]:
            self.stdout.write("Preview selesai; event belum diaktifkan.")
            return
        try:
            activate_event(survey=survey)
        except EventActivationError as exc:
            raise CommandError(str(exc)) from exc

        self.stdout.write(self.style.SUCCESS("Aktivasi event: APPLIED"))
        self.stdout.write("Status: active")
        self.stdout.write("Runtime source: postgresql")
