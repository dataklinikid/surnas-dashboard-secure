import django.core.validators
from django.db import migrations, models


def backfill_metadata_identity(apps, schema_editor):
    SurveyMetadataVersion = apps.get_model("aggregate", "SurveyMetadataVersion")

    active_by_event = {}
    active_by_questionnaire = {}

    def reset_duplicate_event(survey):
        survey.active = False
        survey.status = "draft"
        survey.validation_state = "not_run"
        survey.validated_at = None
        survey.validation_fingerprint = ""
        survey.validation_report = {}
        survey.dashboard_config = {}
        survey.save(
            update_fields=(
                "status",
                "active",
                "validation_state",
                "validated_at",
                "validation_fingerprint",
                "validation_report",
                "dashboard_config",
            )
        )

    def deactivate(metadata, *, reset_event):
        metadata.is_active = False
        metadata.save(
            update_fields=("questionnaire_key", "source_database", "is_active")
        )
        if reset_event:
            reset_duplicate_event(metadata.survey)

    def is_known_clone(metadata):
        return str(metadata.source_name or "").strip().casefold().startswith(
            ("clone:", "template:")
        )

    for metadata in SurveyMetadataVersion.objects.select_related("survey").order_by("pk"):
        survey_payload = metadata.payload.get("survey", {}) if isinstance(metadata.payload, dict) else {}
        questionnaire_key = str(survey_payload.get("dictionary_name", "")).strip().upper()
        if not questionnaire_key:
            questionnaire_key = f"LEGACY_{metadata.survey.code.upper()}"
        try:
            source_database = metadata.survey.data_source.database_name.casefold()
        except Exception:
            source_database = f"legacy_{metadata.survey.code}"[:64].casefold()

        metadata.questionnaire_key = questionnaire_key
        metadata.source_database = source_database
        if not metadata.is_active:
            metadata.save(update_fields=("questionnaire_key", "source_database"))
            continue

        if metadata.survey_id in active_by_event:
            deactivate(metadata, reset_event=False)
            continue

        owner = active_by_questionnaire.get(questionnaire_key)
        if owner is None:
            metadata.save(update_fields=("questionnaire_key", "source_database"))
            active_by_event[metadata.survey_id] = metadata
            active_by_questionnaire[questionnaire_key] = metadata
            continue

        if owner.survey.active and metadata.survey.active:
            owner_is_clone = is_known_clone(owner)
            metadata_is_clone = is_known_clone(metadata)
            if owner_is_clone == metadata_is_clone:
                raise RuntimeError(
                    "Identitas kuesioner aktif digunakan oleh dua event produksi yang tidak "
                    "dapat dibedakan sebagai clone: "
                    f"{owner.survey.code} dan {metadata.survey.code} ({questionnaire_key})."
                )
            if metadata_is_clone:
                deactivate(metadata, reset_event=True)
                continue
            deactivate(owner, reset_event=True)
            metadata.save(update_fields=("questionnaire_key", "source_database"))
            active_by_event[metadata.survey_id] = metadata
            active_by_questionnaire[questionnaire_key] = metadata
            continue
        if metadata.survey.active and not owner.survey.active:
            deactivate(owner, reset_event=True)
            metadata.save(update_fields=("questionnaire_key", "source_database"))
            active_by_event[metadata.survey_id] = metadata
            active_by_questionnaire[questionnaire_key] = metadata
            continue

        deactivate(metadata, reset_event=True)


def isolate_duplicate_reporting_sources(apps, schema_editor):
    SurveyDataSource = apps.get_model("aggregate", "SurveyDataSource")
    owners = {}

    for source in SurveyDataSource.objects.select_related("survey").order_by("pk"):
        if not source.active or source.connection_profile_id is None:
            continue
        key = (source.connection_profile_id, source.database_name.casefold())
        owner = owners.get(key)
        if owner is None:
            owners[key] = source
            continue
        if owner.survey.active and source.survey.active:
            raise RuntimeError(
                "Database reporting digunakan oleh dua event produksi: "
                f"{owner.survey.code} dan {source.survey.code} ({source.database_name})."
            )
        if source.survey.active and not owner.survey.active:
            owner.active = False
            owner.save(update_fields=("active",))
            owners[key] = source
        else:
            source.active = False
            source.save(update_fields=("active",))


class Migration(migrations.Migration):
    dependencies = [("aggregate", "0012_profile_discovery_environment")]

    operations = [
        migrations.AddField(
            model_name="surveymetadataversion",
            name="questionnaire_key",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="surveymetadataversion",
            name="source_database",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.RunPython(backfill_metadata_identity, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="surveymetadataversion",
            name="questionnaire_key",
            field=models.CharField(max_length=255),
        ),
        migrations.AlterField(
            model_name="surveymetadataversion",
            name="source_database",
            field=models.CharField(
                max_length=64,
                validators=[
                    django.core.validators.RegexValidator(
                        message=(
                            "Identifier database harus diawali huruf dan hanya berisi huruf, "
                            "angka, atau underscore."
                        ),
                        regex="^[A-Za-z][A-Za-z0-9_]{0,63}$",
                    )
                ],
            ),
        ),
        migrations.RunPython(isolate_duplicate_reporting_sources, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="surveydatasource",
            constraint=models.UniqueConstraint(
                condition=models.Q(active=True),
                fields=("connection_profile", "database_name"),
                name="unique_profile_reporting_database",
            ),
        ),
        migrations.AddConstraint(
            model_name="surveymetadataversion",
            constraint=models.UniqueConstraint(
                condition=models.Q(is_active=True),
                fields=("survey",),
                name="unique_active_metadata_per_event",
            ),
        ),
        migrations.AddConstraint(
            model_name="surveymetadataversion",
            constraint=models.UniqueConstraint(
                condition=models.Q(is_active=True),
                fields=("questionnaire_key",),
                name="unique_active_questionnaire_metadata",
            ),
        ),
    ]
