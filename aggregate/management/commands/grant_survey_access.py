from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from aggregate.models import SurveyAccess, SurveyMembership


ROLES = {
    "monitor": {"can_monitor": True, "can_analyse": False, "can_export": False},
    "analyst": {"can_monitor": True, "can_analyse": True, "can_export": False},
    "admin": {"can_monitor": True, "can_analyse": True, "can_export": True},
}


class Command(BaseCommand):
    help = "Memberikan akses username ke satu survei berdasarkan role."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--survey", required=True)
        parser.add_argument("--role", required=True, choices=sorted(ROLES))

    def handle(self, *args, **options):
        User = get_user_model()
        try:
            user = User.objects.get(username=options["username"])
        except User.DoesNotExist as exc:
            raise CommandError(f"Username tidak ditemukan: {options['username']}.") from exc
        try:
            survey = SurveyAccess.objects.get(code=options["survey"], active=True)
        except SurveyAccess.DoesNotExist as exc:
            raise CommandError(
                f"Survei belum tersedia pada kontrol akses: {options['survey']}. Jalankan sync_survey_access."
            ) from exc

        membership, created = SurveyMembership.objects.update_or_create(
            user=user,
            survey=survey,
            defaults=ROLES[options["role"]],
        )
        action = "dibuat" if created else "diperbarui"
        self.stdout.write(self.style.SUCCESS("Pemberian akses survei: OK"))
        self.stdout.write(f"Username: {membership.user.username}")
        self.stdout.write(f"Survey: {membership.survey.code}")
        self.stdout.write(f"Role: {options['role']} ({action})")
