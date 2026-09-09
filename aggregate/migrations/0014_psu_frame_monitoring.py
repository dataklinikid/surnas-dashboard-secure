import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("aggregate", "0013_event_metadata_isolation"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SurveyPSUFrame",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version", models.SlugField(max_length=80)),
                ("source_name", models.CharField(max_length=255)),
                ("file_sha256", models.CharField(max_length=64, validators=[django.core.validators.RegexValidator(message="SHA-256 harus terdiri dari 64 karakter hexadecimal huruf kecil.", regex="^[0-9a-f]{64}$")])),
                ("row_count", models.PositiveIntegerField()),
                ("target_total", models.PositiveIntegerField()),
                ("import_report", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_survey_psu_frames", to=settings.AUTH_USER_MODEL)),
                ("survey", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="psu_frames", to="aggregate.surveyaccess")),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="SurveyMonitoringConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("questionnaire_column", models.CharField(blank=True, max_length=64, validators=[django.core.validators.RegexValidator(message="Identifier database harus diawali huruf dan hanya berisi huruf, angka, atau underscore.", regex="^[A-Za-z][A-Za-z0-9_]{0,63}$")])),
                ("enumerator_column", models.CharField(blank=True, max_length=64, validators=[django.core.validators.RegexValidator(message="Identifier database harus diawali huruf dan hanya berisi huruf, angka, atau underscore.", regex="^[A-Za-z][A-Za-z0-9_]{0,63}$")])),
                ("submit_time_column", models.CharField(blank=True, max_length=64, validators=[django.core.validators.RegexValidator(message="Identifier database harus diawali huruf dan hanya berisi huruf, angka, atau underscore.", regex="^[A-Za-z][A-Za-z0-9_]{0,63}$")])),
                ("start_hour_column", models.CharField(blank=True, max_length=64, validators=[django.core.validators.RegexValidator(message="Identifier database harus diawali huruf dan hanya berisi huruf, angka, atau underscore.", regex="^[A-Za-z][A-Za-z0-9_]{0,63}$")])),
                ("start_minute_column", models.CharField(blank=True, max_length=64, validators=[django.core.validators.RegexValidator(message="Identifier database harus diawali huruf dan hanya berisi huruf, angka, atau underscore.", regex="^[A-Za-z][A-Za-z0-9_]{0,63}$")])),
                ("village_column", models.CharField(blank=True, max_length=64, validators=[django.core.validators.RegexValidator(message="Identifier database harus diawali huruf dan hanya berisi huruf, angka, atau underscore.", regex="^[A-Za-z][A-Za-z0-9_]{0,63}$")])),
                ("district_column", models.CharField(blank=True, max_length=64, validators=[django.core.validators.RegexValidator(message="Identifier database harus diawali huruf dan hanya berisi huruf, angka, atau underscore.", regex="^[A-Za-z][A-Za-z0-9_]{0,63}$")])),
                ("regency_column", models.CharField(blank=True, max_length=64, validators=[django.core.validators.RegexValidator(message="Identifier database harus diawali huruf dan hanya berisi huruf, angka, atau underscore.", regex="^[A-Za-z][A-Za-z0-9_]{0,63}$")])),
                ("refresh_seconds", models.PositiveSmallIntegerField(default=60)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("survey", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="monitoring_config", to="aggregate.surveyaccess")),
                ("updated_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="updated_survey_monitoring_configs", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="SurveyPSU",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("psu_number", models.PositiveIntegerField()),
                ("village", models.CharField(max_length=255)),
                ("district", models.CharField(max_length=255)),
                ("regency", models.CharField(max_length=255)),
                ("dpr_ri_constituency", models.CharField(blank=True, max_length=255)),
                ("province", models.CharField(max_length=255)),
                ("urban_rural", models.CharField(max_length=40)),
                ("target_n", models.PositiveIntegerField()),
                ("questionnaire_start", models.PositiveIntegerField()),
                ("questionnaire_end", models.PositiveIntegerField()),
                ("normalized_location_key", models.CharField(max_length=800)),
                ("frame", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="psus", to="aggregate.surveypsuframe")),
            ],
            options={"ordering": ("psu_number",)},
        ),
        migrations.AddConstraint(model_name="surveypsuframe", constraint=models.UniqueConstraint(fields=("survey", "version"), name="unique_survey_psu_frame_version")),
        migrations.AddConstraint(model_name="surveypsuframe", constraint=models.UniqueConstraint(condition=models.Q(("is_active", True)), fields=("survey",), name="unique_active_psu_frame_per_event")),
        migrations.AddIndex(model_name="surveypsuframe", index=models.Index(fields=["survey", "is_active"], name="psuframe_active_idx")),
        migrations.AddConstraint(model_name="surveypsu", constraint=models.UniqueConstraint(fields=("frame", "psu_number"), name="unique_psu_number_per_frame")),
        migrations.AddConstraint(model_name="surveypsu", constraint=models.CheckConstraint(condition=models.Q(("questionnaire_end__gte", models.F("questionnaire_start"))), name="psu_questionnaire_range_valid")),
        migrations.AddIndex(model_name="surveypsu", index=models.Index(fields=["frame", "questionnaire_start"], name="psu_qstart_idx")),
    ]
