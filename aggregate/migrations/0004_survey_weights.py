from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("aggregate", "0003_surveymembership"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="SurveyWeightSet",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("version", models.SlugField(max_length=80)),
                ("method", models.CharField(blank=True, max_length=160)),
                ("key_column", models.CharField(default="Q_AC", max_length=64)),
                ("weight_column", models.CharField(default="WEIGHT", max_length=64)),
                ("file_sha256", models.CharField(max_length=64)),
                ("dataset_fingerprint", models.CharField(max_length=64)),
                ("source_row_count", models.PositiveIntegerField()),
                ("matched_count", models.PositiveIntegerField()),
                ("coverage", models.DecimalField(decimal_places=4, max_digits=7)),
                ("weight_sum", models.DecimalField(decimal_places=10, max_digits=24)),
                ("weight_min", models.DecimalField(decimal_places=10, max_digits=24)),
                ("weight_max", models.DecimalField(decimal_places=10, max_digits=24)),
                ("weight_mean", models.DecimalField(decimal_places=10, max_digits=24)),
                ("effective_sample_size", models.DecimalField(decimal_places=10, max_digits=24)),
                ("is_active", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_survey_weight_sets", to=settings.AUTH_USER_MODEL)),
                ("survey", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="weight_sets", to="aggregate.surveyaccess")),
            ],
        ),
        migrations.CreateModel(
            name="SurveyWeight",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("respondent_key", models.CharField(max_length=255)),
                ("weight", models.DecimalField(decimal_places=10, max_digits=24)),
                ("weight_set", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="weights", to="aggregate.surveyweightset")),
            ],
        ),
        migrations.AddConstraint(
            model_name="surveyweightset",
            constraint=models.UniqueConstraint(fields=("survey", "version"), name="unique_survey_weight_version"),
        ),
        migrations.AddIndex(
            model_name="surveyweightset",
            index=models.Index(fields=["survey", "is_active"], name="weightset_active_idx"),
        ),
        migrations.AddConstraint(
            model_name="surveyweight",
            constraint=models.UniqueConstraint(fields=("weight_set", "respondent_key"), name="unique_weightset_respondent"),
        ),
        migrations.AddIndex(
            model_name="surveyweight",
            index=models.Index(fields=["weight_set", "respondent_key"], name="weightset_key_idx"),
        ),
    ]
