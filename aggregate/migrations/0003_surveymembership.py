from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


def migrate_legacy_access(apps, schema_editor):
    User = apps.get_model("auth", "User")
    SurveyAccess = apps.get_model("aggregate", "SurveyAccess")
    SurveyMembership = apps.get_model("aggregate", "SurveyMembership")
    survey = SurveyAccess.objects.filter(code="surnasfeb26").first()
    if not survey:
        survey = SurveyAccess.objects.filter(code="surnasdes26").first()
        if survey:
            survey.code = "surnasfeb26"
            survey.name = "Survei Nasional PDAT Februari 2026"
            survey.save(update_fields=["code", "name"])
    if not survey:
        return

    monitor_code = "access_surnasdes26_monitoring"
    analysis_code = "access_surnasdes26_analysis"
    export_code = "export_surnasdes26"
    for user in User.objects.all():
        direct = set(user.user_permissions.values_list("codename", flat=True))
        group = set(
            user.groups.values_list("permissions__codename", flat=True).exclude(
                permissions__codename__isnull=True
            )
        )
        codes = direct | group
        if not codes.intersection({monitor_code, analysis_code, export_code}):
            continue
        SurveyMembership.objects.update_or_create(
            user=user,
            survey=survey,
            defaults={
                "can_monitor": monitor_code in codes or analysis_code in codes or export_code in codes,
                "can_analyse": analysis_code in codes or export_code in codes,
                "can_export": export_code in codes,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("aggregate", "0002_update_surnasfeb26_labels"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SurveyMembership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("can_monitor", models.BooleanField(default=True)),
                ("can_analyse", models.BooleanField(default=False)),
                ("can_export", models.BooleanField(default=False)),
                ("survey", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="aggregate.surveyaccess")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="survey_memberships", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name="surveymembership",
            constraint=models.UniqueConstraint(fields=("user", "survey"), name="unique_user_survey_membership"),
        ),
        migrations.RunPython(migrate_legacy_access, migrations.RunPython.noop),
    ]
