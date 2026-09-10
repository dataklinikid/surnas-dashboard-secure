import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("aggregate", "0006_survey_runtime_config"),
    ]

    operations = [
        migrations.AddField(
            model_name="surveyaccess",
            name="validated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="surveyaccess",
            name="validation_fingerprint",
            field=models.CharField(blank=True, max_length=64, validators=[django.core.validators.RegexValidator(message="SHA-256 harus terdiri dari 64 karakter hexadecimal huruf kecil.", regex="^[0-9a-f]{64}$")]),
        ),
        migrations.AddField(
            model_name="surveyaccess",
            name="validation_report",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="surveyaccess",
            name="validation_state",
            field=models.CharField(choices=[("not_run", "Belum divalidasi"), ("passed", "Lulus"), ("failed", "Gagal")], default="not_run", max_length=16),
        ),
    ]
