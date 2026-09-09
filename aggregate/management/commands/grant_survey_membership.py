from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from aggregate.access_roles import ROLE_CAPABILITIES
from aggregate.models import SurveyAccess, SurveyMembership


class Command(BaseCommand):
    help = "Memberikan atau memperbarui membership pada event tervalidasi atau aktif."

    def add_arguments(self, parser):
        parser.add_argument("--survey", required=True)
        parser.add_argument("--username", required=True)
        parser.add_argument("--role", required=True, choices=sorted(ROLE_CAPABILITIES))
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        code = options["survey"].strip().lower()
        username = options["username"].strip()
        role = options["role"]
        try:
            survey = SurveyAccess.objects.get(code=code, validation_state=SurveyAccess.ValidationState.PASSED)
        except SurveyAccess.DoesNotExist as exc:
            raise CommandError("Event yang telah lulus validasi tidak ditemukan.") from exc
        try:
            user = get_user_model().objects.get(username=username, is_active=True)
        except get_user_model().DoesNotExist as exc:
            raise CommandError("Pengguna aktif tidak ditemukan.") from exc

        capabilities = ROLE_CAPABILITIES[role]
        existing = SurveyMembership.objects.filter(user=user, survey=survey).first()
        self.stdout.write(
            "Grant survey membership: APPLY"
            if options["apply"]
            else "Grant survey membership: PREVIEW"
        )
        self.stdout.write(f"Survey code: {survey.code}")
        self.stdout.write(f"Username: {user.username}")
        self.stdout.write(f"Role: {role}")
        self.stdout.write(f"Existing membership: {'ya' if existing else 'tidak'}")
        self.stdout.write(f"Can monitor: {str(capabilities['can_monitor']).lower()}")
        self.stdout.write(f"Can analyse: {str(capabilities['can_analyse']).lower()}")
        self.stdout.write(f"Can export: {str(capabilities['can_export']).lower()}")
        if not options["apply"]:
            self.stdout.write("Preview selesai; membership belum diubah.")
            return

        with transaction.atomic():
            membership, created = SurveyMembership.objects.update_or_create(
                user=user,
                survey=survey,
                defaults=capabilities,
            )
        self.stdout.write(self.style.SUCCESS("Grant survey membership: APPLIED"))
        self.stdout.write(f"Membership ID: {membership.pk}")
        self.stdout.write(f"Created: {str(created).lower()}")
