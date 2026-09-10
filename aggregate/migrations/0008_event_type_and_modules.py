import django.core.validators
from django.db import migrations, models
import django.db.models.deletion


EVENT_TYPES = (
    ("opinion_survey", "Survei Opini", "Survei opini publik, sosial, politik, atau kepuasan."),
    ("quick_count", "Quick Count", "Pengumpulan dan estimasi hasil pemilihan dari sampel TPS."),
    ("field_operation", "Operasi Lapangan", "Monitoring pekerjaan lapangan tanpa tabulasi survei utama."),
    ("combined", "Event Gabungan", "Event yang menggabungkan survei, operasi lapangan, dan modul elektoral."),
)

MODULES = (
    ("fieldwork_monitoring", "Monitoring Lapangan", 10),
    ("survey_analytics", "Analisis Survei", 20),
    ("weighted_analysis", "Analisis Berbobot", 30),
    ("sampling_frame", "Sampling Frame dan PSU", 40),
    ("reporting", "Reporting", 50),
    ("quick_count", "Quick Count", 60),
    ("personnel_monitoring", "Monitoring Personel", 70),
)


def seed_event_catalog(apps, schema_editor):
    EventType = apps.get_model("aggregate", "EventType")
    EventModuleDefinition = apps.get_model("aggregate", "EventModuleDefinition")
    SurveyAccess = apps.get_model("aggregate", "SurveyAccess")
    SurveyEventModule = apps.get_model("aggregate", "SurveyEventModule")

    for code, name, description in EVENT_TYPES:
        EventType.objects.update_or_create(
            code=code,
            defaults={"name": name, "description": description, "active": True},
        )
    for code, name, display_order in MODULES:
        EventModuleDefinition.objects.update_or_create(
            code=code,
            defaults={"name": name, "display_order": display_order, "active": True},
        )

    opinion_survey = EventType.objects.get(code="opinion_survey")
    default_modules = EventModuleDefinition.objects.filter(
        code__in=("fieldwork_monitoring", "survey_analytics", "weighted_analysis")
    )
    for survey in SurveyAccess.objects.all():
        if survey.event_type_id is None:
            survey.event_type = opinion_survey
            survey.save(update_fields=("event_type",))
        for module in default_modules:
            SurveyEventModule.objects.get_or_create(
                survey=survey,
                module=module,
                defaults={"enabled": True, "readiness": "ready", "config": {}},
            )


class Migration(migrations.Migration):
    dependencies = [("aggregate", "0007_survey_validation_state")]

    operations = [
        migrations.CreateModel(
            name="EventModuleDefinition",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=64, unique=True, validators=[django.core.validators.RegexValidator(message="Kode harus diawali huruf kecil dan hanya berisi huruf kecil, angka, atau underscore.", regex="^[a-z][a-z0-9_]{2,63}$")])),
                ("name", models.CharField(max_length=160)),
                ("description", models.TextField(blank=True)),
                ("active", models.BooleanField(default=True)),
                ("display_order", models.PositiveSmallIntegerField(default=0)),
            ],
            options={"ordering": ("display_order", "name")},
        ),
        migrations.CreateModel(
            name="EventType",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=64, unique=True, validators=[django.core.validators.RegexValidator(message="Kode harus diawali huruf kecil dan hanya berisi huruf kecil, angka, atau underscore.", regex="^[a-z][a-z0-9_]{2,63}$")])),
                ("name", models.CharField(max_length=160)),
                ("description", models.TextField(blank=True)),
                ("active", models.BooleanField(default=True)),
            ],
            options={"ordering": ("name",)},
        ),
        migrations.AddField(
            model_name="surveyaccess",
            name="event_type",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="events", to="aggregate.eventtype"),
        ),
        migrations.CreateModel(
            name="SurveyEventModule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("enabled", models.BooleanField(default=True)),
                ("readiness", models.CharField(choices=[("pending", "Belum dikonfigurasi"), ("ready", "Siap"), ("blocked", "Terhambat")], default="pending", max_length=16)),
                ("config", models.JSONField(blank=True, default=dict)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("module", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="event_assignments", to="aggregate.eventmoduledefinition")),
                ("survey", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="event_modules", to="aggregate.surveyaccess")),
            ],
            options={"ordering": ("module__display_order", "module__name")},
        ),
        migrations.AddConstraint(
            model_name="surveyeventmodule",
            constraint=models.UniqueConstraint(fields=("survey", "module"), name="unique_survey_event_module"),
        ),
        migrations.RunPython(seed_event_catalog, migrations.RunPython.noop),
    ]
