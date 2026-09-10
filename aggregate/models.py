from django.conf import settings
from django.core.validators import RegexValidator
from django.db import models


LOWER_CODE_VALIDATOR = RegexValidator(
    regex=r"^[a-z][a-z0-9_]{2,63}$",
    message="Kode harus diawali huruf kecil dan hanya berisi huruf kecil, angka, atau underscore.",
)
ENV_PREFIX_VALIDATOR = RegexValidator(
    regex=r"^[A-Z][A-Z0-9_]{2,63}$",
    message="Environment prefix hanya boleh berisi huruf kapital, angka, atau underscore.",
)
SQL_IDENTIFIER_VALIDATOR = RegexValidator(
    regex=r"^[A-Za-z][A-Za-z0-9_]{0,63}$",
    message="Identifier database harus diawali huruf dan hanya berisi huruf, angka, atau underscore.",
)
SHA256_VALIDATOR = RegexValidator(
    regex=r"^[0-9a-f]{64}$",
    message="SHA-256 harus terdiri dari 64 karakter hexadecimal huruf kecil.",
)


class Region(models.Model):
    class Level(models.TextChoices):
        NATIONAL = "national", "Nasional"
        PROVINCE = "province", "Provinsi"
        REGENCY = "regency", "Kabupaten/Kota"
        DISTRICT = "district", "Kecamatan"
        VILLAGE = "village", "Desa/Kelurahan"
        OTHER = "other", "Lainnya"

    code = models.CharField(max_length=64, unique=True, validators=[LOWER_CODE_VALIDATOR])
    name = models.CharField(max_length=160)
    level = models.CharField(max_length=16, choices=Level.choices)
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ("level", "name")

    def __str__(self):
        return self.name


class SurveyProgram(models.Model):
    code = models.CharField(max_length=64, unique=True, validators=[LOWER_CODE_VALIDATOR])
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class EventType(models.Model):
    code = models.CharField(max_length=64, unique=True, validators=[LOWER_CODE_VALIDATOR])
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class EventModuleDefinition(models.Model):
    code = models.CharField(max_length=64, unique=True, validators=[LOWER_CODE_VALIDATOR])
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)
    display_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ("display_order", "name")

    def __str__(self):
        return self.name


class SurveyAccess(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        VALIDATION = "validation", "Validasi"
        ACTIVE = "active", "Aktif"
        ARCHIVED = "archived", "Diarsipkan"

    class ValidationState(models.TextChoices):
        NOT_RUN = "not_run", "Belum divalidasi"
        PASSED = "passed", "Lulus"
        FAILED = "failed", "Gagal"

    code = models.SlugField(unique=True)
    name = models.CharField(max_length=120)
    event_type = models.ForeignKey(
        EventType,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="events",
    )
    program = models.ForeignKey(
        SurveyProgram,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="events",
    )
    region = models.ForeignKey(
        Region,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="survey_events",
    )
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    dashboard_config = models.JSONField(default=dict, blank=True)
    privacy_config = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    validation_state = models.CharField(
        max_length=16,
        choices=ValidationState.choices,
        default=ValidationState.NOT_RUN,
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    validation_fingerprint = models.CharField(
        max_length=64,
        blank=True,
        validators=[SHA256_VALIDATOR],
    )
    validation_report = models.JSONField(default=dict, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        permissions = [
            ("access_surnasdes26_monitoring", "Dapat melihat monitoring Surnas Februari 2026"),
            ("access_surnasdes26_analysis", "Dapat melihat analisis Surnas Februari 2026"),
            ("export_surnasdes26", "Dapat mengekspor data Surnas Februari 2026"),
        ]

    def __str__(self):
        return self.name


class SurveyEventModule(models.Model):
    class Readiness(models.TextChoices):
        PENDING = "pending", "Belum dikonfigurasi"
        READY = "ready", "Siap"
        BLOCKED = "blocked", "Terhambat"

    survey = models.ForeignKey(
        SurveyAccess,
        on_delete=models.CASCADE,
        related_name="event_modules",
    )
    module = models.ForeignKey(
        EventModuleDefinition,
        on_delete=models.PROTECT,
        related_name="event_assignments",
    )
    enabled = models.BooleanField(default=True)
    readiness = models.CharField(
        max_length=16,
        choices=Readiness.choices,
        default=Readiness.PENDING,
    )
    config = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("survey", "module"),
                name="unique_survey_event_module",
            )
        ]
        ordering = ("module__display_order", "module__name")

    def __str__(self):
        return f"{self.survey.code} - {self.module.name}"


class SurveyConnectionProfile(models.Model):
    class Engine(models.TextChoices):
        MARIADB = "mariadb", "MariaDB/MySQL"

    code = models.CharField(max_length=64, unique=True, validators=[LOWER_CODE_VALIDATOR])
    name = models.CharField(max_length=160)
    engine = models.CharField(max_length=16, choices=Engine.choices, default=Engine.MARIADB)
    environment_prefix = models.CharField(
        max_length=64,
        validators=[ENV_PREFIX_VALIDATOR],
        help_text="Prefix environment variable; tidak menyimpan host, user, atau password.",
    )
    discovery_environment_prefix = models.CharField(
        max_length=64,
        blank=True,
        validators=[ENV_PREFIX_VALIDATOR],
        help_text=(
            "Prefix kredensial read-only untuk Source Catalog. Jika kosong, catalog memakai "
            "environment prefix runtime."
        ),
    )
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name


class SurveyDataSource(models.Model):
    class Engine(models.TextChoices):
        MARIADB = "mariadb", "MariaDB/MySQL"

    survey = models.OneToOneField(
        SurveyAccess,
        on_delete=models.CASCADE,
        related_name="data_source",
    )
    connection_profile = models.ForeignKey(
        SurveyConnectionProfile,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="data_sources",
    )
    engine = models.CharField(max_length=16, choices=Engine.choices, default=Engine.MARIADB)
    connection_alias = models.CharField(
        max_length=64,
        validators=[LOWER_CODE_VALIDATOR],
        help_text="Nama logis koneksi; bukan username atau password database.",
    )
    environment_prefix = models.CharField(
        max_length=64,
        validators=[ENV_PREFIX_VALIDATOR],
        help_text="Prefix environment variable yang menyimpan host, port, user, dan password.",
    )
    database_name = models.CharField(max_length=64, validators=[SQL_IDENTIFIER_VALIDATOR])
    table_name = models.CharField(max_length=64, default="h0", validators=[SQL_IDENTIFIER_VALIDATOR])
    identity_column = models.CharField(
        max_length=64,
        default="Q_AC",
        validators=[SQL_IDENTIFIER_VALIDATOR],
    )
    latest_id_column = models.CharField(
        max_length=64,
        blank=True,
        validators=[SQL_IDENTIFIER_VALIDATOR],
    )
    valid_column = models.CharField(
        max_length=64,
        blank=True,
        validators=[SQL_IDENTIFIER_VALIDATOR],
    )
    valid_value = models.CharField(max_length=120, blank=True)
    target_n = models.PositiveIntegerField(null=True, blank=True)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.survey.code} - {self.database_name}.{self.table_name}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("connection_profile", "database_name"),
                condition=models.Q(active=True),
                name="unique_profile_reporting_database",
            )
        ]


class SurveyMetadataVersion(models.Model):
    survey = models.ForeignKey(
        SurveyAccess,
        on_delete=models.CASCADE,
        related_name="metadata_versions",
    )
    version = models.SlugField(max_length=80)
    metadata_schema_version = models.PositiveSmallIntegerField(default=1)
    questionnaire_key = models.CharField(max_length=255)
    source_database = models.CharField(max_length=64, validators=[SQL_IDENTIFIER_VALIDATOR])
    payload = models.JSONField()
    sha256 = models.CharField(max_length=64, validators=[SHA256_VALIDATOR])
    source_name = models.CharField(max_length=255, blank=True)
    onboarding_report = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_survey_metadata_versions",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("survey", "version"),
                name="unique_survey_metadata_version",
            ),
            models.UniqueConstraint(
                fields=("survey",),
                condition=models.Q(is_active=True),
                name="unique_active_metadata_per_event",
            ),
            models.UniqueConstraint(
                fields=("questionnaire_key",),
                condition=models.Q(is_active=True),
                name="unique_active_questionnaire_metadata",
            ),
        ]
        indexes = [
            models.Index(fields=("survey", "is_active"), name="metadata_active_idx"),
        ]

    def __str__(self):
        return f"{self.survey.code} - {self.version}"


class SurveyPSUFrame(models.Model):
    survey = models.ForeignKey(
        SurveyAccess,
        on_delete=models.CASCADE,
        related_name="psu_frames",
    )
    version = models.SlugField(max_length=80)
    source_name = models.CharField(max_length=255)
    file_sha256 = models.CharField(max_length=64, validators=[SHA256_VALIDATOR])
    row_count = models.PositiveIntegerField()
    target_total = models.PositiveIntegerField()
    import_report = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_survey_psu_frames",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("survey", "version"),
                name="unique_survey_psu_frame_version",
            ),
            models.UniqueConstraint(
                fields=("survey",),
                condition=models.Q(is_active=True),
                name="unique_active_psu_frame_per_event",
            ),
        ]
        indexes = [
            models.Index(fields=("survey", "is_active"), name="psuframe_active_idx"),
        ]
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.survey.code} - {self.version}"


class SurveyPSU(models.Model):
    frame = models.ForeignKey(
        SurveyPSUFrame,
        on_delete=models.CASCADE,
        related_name="psus",
    )
    psu_number = models.PositiveIntegerField()
    village = models.CharField(max_length=255)
    district = models.CharField(max_length=255)
    regency = models.CharField(max_length=255)
    dpr_ri_constituency = models.CharField(max_length=255, blank=True)
    province = models.CharField(max_length=255)
    urban_rural = models.CharField(max_length=40)
    target_n = models.PositiveIntegerField()
    questionnaire_start = models.PositiveIntegerField()
    questionnaire_end = models.PositiveIntegerField()
    normalized_location_key = models.CharField(max_length=800)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("frame", "psu_number"),
                name="unique_psu_number_per_frame",
            ),
            models.CheckConstraint(
                condition=models.Q(questionnaire_end__gte=models.F("questionnaire_start")),
                name="psu_questionnaire_range_valid",
            ),
        ]
        indexes = [
            models.Index(fields=("frame", "questionnaire_start"), name="psu_qstart_idx"),
        ]
        ordering = ("psu_number",)

    def __str__(self):
        return f"{self.frame} - PSU {self.psu_number}"


class SurveyMonitoringConfig(models.Model):
    survey = models.OneToOneField(
        SurveyAccess,
        on_delete=models.CASCADE,
        related_name="monitoring_config",
    )
    questionnaire_column = models.CharField(
        max_length=64,
        blank=True,
        validators=[SQL_IDENTIFIER_VALIDATOR],
    )
    enumerator_column = models.CharField(
        max_length=64,
        blank=True,
        validators=[SQL_IDENTIFIER_VALIDATOR],
    )
    submit_time_column = models.CharField(
        max_length=64,
        blank=True,
        validators=[SQL_IDENTIFIER_VALIDATOR],
    )
    start_hour_column = models.CharField(
        max_length=64,
        blank=True,
        validators=[SQL_IDENTIFIER_VALIDATOR],
    )
    start_minute_column = models.CharField(
        max_length=64,
        blank=True,
        validators=[SQL_IDENTIFIER_VALIDATOR],
    )
    village_column = models.CharField(
        max_length=64,
        blank=True,
        validators=[SQL_IDENTIFIER_VALIDATOR],
    )
    district_column = models.CharField(
        max_length=64,
        blank=True,
        validators=[SQL_IDENTIFIER_VALIDATOR],
    )
    regency_column = models.CharField(
        max_length=64,
        blank=True,
        validators=[SQL_IDENTIFIER_VALIDATOR],
    )
    refresh_seconds = models.PositiveSmallIntegerField(default=60)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="updated_survey_monitoring_configs",
    )

    def __str__(self):
        return f"{self.survey.code} monitoring"


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
    parent_weight_set = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reused_versions",
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
