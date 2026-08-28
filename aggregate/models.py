from django.db import models
from django.conf import settings


class SurveyAccess(models.Model):
    code = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    active = models.BooleanField(default=True)

    class Meta:
        permissions = [
            ("access_surnasdes26_monitoring", "Dapat melihat monitoring Surnas Februari 2026"),
            ("access_surnasdes26_analysis", "Dapat melihat analisis Surnas Februari 2026"),
            ("export_surnasdes26", "Dapat mengekspor data Surnas Februari 2026"),
        ]

    def __str__(self):
        return self.name


class SurveyMembership(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="survey_memberships",
    )
    survey = models.ForeignKey(
        SurveyAccess,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    can_monitor = models.BooleanField(default=True)
    can_analyse = models.BooleanField(default=False)
    can_export = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "survey"),
                name="unique_user_survey_membership",
            )
        ]

    def __str__(self):
        return f"{self.user} - {self.survey.code}"


class SurveyWeightSet(models.Model):
    survey = models.ForeignKey(
        SurveyAccess,
        on_delete=models.CASCADE,
        related_name="weight_sets",
    )
    version = models.SlugField(max_length=80)
    method = models.CharField(max_length=160, blank=True)
    key_column = models.CharField(max_length=64, default="Q_AC")
    weight_column = models.CharField(max_length=64, default="WEIGHT")
    file_sha256 = models.CharField(max_length=64)
    dataset_fingerprint = models.CharField(max_length=64)
    source_row_count = models.PositiveIntegerField()
    matched_count = models.PositiveIntegerField()
    coverage = models.DecimalField(max_digits=7, decimal_places=4)
    weight_sum = models.DecimalField(max_digits=24, decimal_places=10)
    weight_min = models.DecimalField(max_digits=24, decimal_places=10)
    weight_max = models.DecimalField(max_digits=24, decimal_places=10)
    weight_mean = models.DecimalField(max_digits=24, decimal_places=10)
    effective_sample_size = models.DecimalField(max_digits=24, decimal_places=10)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_survey_weight_sets",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("survey", "version"),
                name="unique_survey_weight_version",
            )
        ]
        indexes = [
            models.Index(fields=("survey", "is_active"), name="weightset_active_idx"),
        ]

    def __str__(self):
        return f"{self.survey.code} - {self.version}"


class SurveyWeight(models.Model):
    weight_set = models.ForeignKey(
        SurveyWeightSet,
        on_delete=models.CASCADE,
        related_name="weights",
    )
    respondent_key = models.CharField(max_length=255)
    weight = models.DecimalField(max_digits=24, decimal_places=10)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("weight_set", "respondent_key"),
                name="unique_weightset_respondent",
            )
        ]
        indexes = [
            models.Index(
                fields=("weight_set", "respondent_key"),
                name="weightset_key_idx",
            )
        ]

    def __str__(self):
        return f"{self.weight_set} - {self.respondent_key}"
