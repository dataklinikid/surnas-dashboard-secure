import django.core.validators
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("aggregate", "0004_survey_weights"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Region",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=64, unique=True, validators=[django.core.validators.RegexValidator(message="Kode harus diawali huruf kecil dan hanya berisi huruf kecil, angka, atau underscore.", regex="^[a-z][a-z0-9_]{2,63}$")])),
                ("name", models.CharField(max_length=160)),
                ("level", models.CharField(choices=[("national", "Nasional"), ("province", "Provinsi"), ("regency", "Kabupaten/Kota"), ("district", "Kecamatan"), ("village", "Desa/Kelurahan"), ("other", "Lainnya")], max_length=16)),
                ("active", models.BooleanField(default=True)),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="children", to="aggregate.region")),
            ],
            options={"ordering": ("level", "name")},
        ),
        migrations.CreateModel(
            name="SurveyProgram",
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
            name="period_end",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="surveyaccess",
            name="period_start",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="surveyaccess",
            name="program",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="events", to="aggregate.surveyprogram"),
        ),
        migrations.AddField(
            model_name="surveyaccess",
            name="region",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="survey_events", to="aggregate.region"),
        ),
        migrations.AddField(
            model_name="surveyaccess",
            name="status",
            field=models.CharField(choices=[("draft", "Draft"), ("validation", "Validasi"), ("active", "Aktif"), ("archived", "Diarsipkan")], default="active", max_length=16),
        ),
        migrations.CreateModel(
            name="SurveyDataSource",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("engine", models.CharField(choices=[("mariadb", "MariaDB/MySQL")], default="mariadb", max_length=16)),
                ("connection_alias", models.CharField(help_text="Nama logis koneksi; bukan username atau password database.", max_length=64, validators=[django.core.validators.RegexValidator(message="Kode harus diawali huruf kecil dan hanya berisi huruf kecil, angka, atau underscore.", regex="^[a-z][a-z0-9_]{2,63}$")])),
                ("environment_prefix", models.CharField(help_text="Prefix environment variable yang menyimpan host, port, user, dan password.", max_length=64, validators=[django.core.validators.RegexValidator(message="Environment prefix hanya boleh berisi huruf kapital, angka, atau underscore.", regex="^[A-Z][A-Z0-9_]{2,63}$")])),
                ("database_name", models.CharField(max_length=64, validators=[django.core.validators.RegexValidator(message="Identifier database harus diawali huruf dan hanya berisi huruf, angka, atau underscore.", regex="^[A-Za-z][A-Za-z0-9_]{0,63}$")])),
                ("table_name", models.CharField(default="h0", max_length=64, validators=[django.core.validators.RegexValidator(message="Identifier database harus diawali huruf dan hanya berisi huruf, angka, atau underscore.", regex="^[A-Za-z][A-Za-z0-9_]{0,63}$")])),
                ("identity_column", models.CharField(default="Q_AC", max_length=64, validators=[django.core.validators.RegexValidator(message="Identifier database harus diawali huruf dan hanya berisi huruf, angka, atau underscore.", regex="^[A-Za-z][A-Za-z0-9_]{0,63}$")])),
                ("latest_id_column", models.CharField(blank=True, max_length=64, validators=[django.core.validators.RegexValidator(message="Identifier database harus diawali huruf dan hanya berisi huruf, angka, atau underscore.", regex="^[A-Za-z][A-Za-z0-9_]{0,63}$")])),
                ("valid_column", models.CharField(blank=True, max_length=64, validators=[django.core.validators.RegexValidator(message="Identifier database harus diawali huruf dan hanya berisi huruf, angka, atau underscore.", regex="^[A-Za-z][A-Za-z0-9_]{0,63}$")])),
                ("valid_value", models.CharField(blank=True, max_length=120)),
                ("target_n", models.PositiveIntegerField(blank=True, null=True)),
                ("active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("survey", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="data_source", to="aggregate.surveyaccess")),
            ],
        ),
        migrations.CreateModel(
            name="SurveyMetadataVersion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version", models.SlugField(max_length=80)),
                ("metadata_schema_version", models.PositiveSmallIntegerField(default=1)),
                ("payload", models.JSONField()),
                ("sha256", models.CharField(max_length=64, validators=[django.core.validators.RegexValidator(message="SHA-256 harus terdiri dari 64 karakter hexadecimal huruf kecil.", regex="^[0-9a-f]{64}$")])),
                ("source_name", models.CharField(blank=True, max_length=255)),
                ("is_active", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_survey_metadata_versions", to=settings.AUTH_USER_MODEL)),
                ("survey", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="metadata_versions", to="aggregate.surveyaccess")),
            ],
        ),
        migrations.AddConstraint(
            model_name="surveymetadataversion",
            constraint=models.UniqueConstraint(fields=("survey", "version"), name="unique_survey_metadata_version"),
        ),
        migrations.AddIndex(
            model_name="surveymetadataversion",
            index=models.Index(fields=["survey", "is_active"], name="metadata_active_idx"),
        ),
    ]
