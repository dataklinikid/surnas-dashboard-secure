from django.contrib import admin

from .models import (
    EventModuleDefinition,
    EventType,
    Region,
    SurveyAccess,
    SurveyConnectionProfile,
    SurveyDataSource,
    SurveyEventModule,
    SurveyMembership,
    SurveyMetadataVersion,
    SurveyMonitoringConfig,
    SurveyPSU,
    SurveyPSUFrame,
    SurveyProgram,
    SurveyWeightSet,
)


class SurveyMembershipInline(admin.TabularInline):
    model = SurveyMembership
    extra = 0


class SurveyDataSourceInline(admin.StackedInline):
    model = SurveyDataSource
    extra = 0
    max_num = 1


class SurveyEventModuleInline(admin.TabularInline):
    model = SurveyEventModule
    extra = 0


class SurveyPSUInline(admin.TabularInline):
    model = SurveyPSU
    extra = 0
    can_delete = False
    readonly_fields = (
        "psu_number", "village", "district", "regency", "dpr_ri_constituency",
        "province", "urban_rural", "target_n", "questionnaire_start",
        "questionnaire_end", "normalized_location_key",
    )


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "level", "parent", "active")
    list_filter = ("level", "active")
    search_fields = ("code", "name")


@admin.register(SurveyProgram)
class SurveyProgramAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "active")
    list_filter = ("active",)
    search_fields = ("code", "name")


@admin.register(EventType)
class EventTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "active")
    list_filter = ("active",)
    search_fields = ("code", "name")


@admin.register(EventModuleDefinition)
class EventModuleDefinitionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "display_order", "active")
    list_filter = ("active",)
    search_fields = ("code", "name")
    ordering = ("display_order", "name")


@admin.register(SurveyConnectionProfile)
class SurveyConnectionProfileAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "engine",
        "environment_prefix",
        "discovery_environment_prefix",
        "active",
    )
    list_filter = ("engine", "active")
    search_fields = (
        "code",
        "name",
        "environment_prefix",
        "discovery_environment_prefix",
    )


@admin.register(SurveyAccess)
class SurveyAccessAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "event_type",
        "program",
        "region",
        "status",
        "validation_state",
        "active",
    )
    list_filter = (
        "event_type",
        "status",
        "validation_state",
        "active",
        "program",
        "region__level",
    )
    search_fields = ("code", "name")
    readonly_fields = ("validation_state", "validated_at", "validation_fingerprint", "validation_report")
    inlines = (SurveyDataSourceInline, SurveyEventModuleInline, SurveyMembershipInline)


@admin.register(SurveyEventModule)
class SurveyEventModuleAdmin(admin.ModelAdmin):
    list_display = ("survey", "module", "enabled", "readiness", "updated_at")
    list_filter = ("module", "enabled", "readiness")
    search_fields = ("survey__code", "survey__name", "module__code", "module__name")


@admin.register(SurveyMembership)
class SurveyMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "survey", "can_monitor", "can_analyse", "can_export")
    list_filter = ("survey", "can_monitor", "can_analyse", "can_export")
    search_fields = ("user__username", "survey__code", "survey__name")


@admin.register(SurveyMetadataVersion)
class SurveyMetadataVersionAdmin(admin.ModelAdmin):
    list_display = (
        "survey",
        "questionnaire_key",
        "source_database",
        "version",
        "metadata_schema_version",
        "is_active",
        "created_at",
    )
    list_filter = ("survey", "is_active", "metadata_schema_version")
    search_fields = (
        "survey__code",
        "questionnaire_key",
        "source_database",
        "version",
        "sha256",
        "source_name",
    )
    readonly_fields = (
        "questionnaire_key",
        "source_database",
        "sha256",
        "onboarding_report",
        "created_at",
        "created_by",
    )


@admin.register(SurveyPSUFrame)
class SurveyPSUFrameAdmin(admin.ModelAdmin):
    list_display = ("survey", "version", "row_count", "target_total", "is_active", "created_at")
    list_filter = ("survey", "is_active")
    search_fields = ("survey__code", "version", "source_name", "file_sha256")
    readonly_fields = (
        "source_name", "file_sha256", "row_count", "target_total", "import_report",
        "is_active", "created_at", "created_by",
    )
    inlines = (SurveyPSUInline,)


@admin.register(SurveyMonitoringConfig)
class SurveyMonitoringConfigAdmin(admin.ModelAdmin):
    list_display = ("survey", "questionnaire_column", "enumerator_column", "refresh_seconds", "updated_at")
    search_fields = ("survey__code", "survey__name", "questionnaire_column")
    readonly_fields = ("updated_at", "updated_by")


@admin.register(SurveyWeightSet)
class SurveyWeightSetAdmin(admin.ModelAdmin):
    list_display = (
        "survey",
        "version",
        "parent_weight_set",
        "coverage",
        "weight_sum",
        "is_active",
        "created_at",
    )
    list_filter = ("survey", "is_active")
    search_fields = ("survey__code", "version", "method", "file_sha256")
    readonly_fields = (
        "file_sha256",
        "parent_weight_set",
        "dataset_fingerprint",
        "source_row_count",
        "matched_count",
        "coverage",
        "weight_sum",
        "weight_min",
        "weight_max",
        "weight_mean",
        "effective_sample_size",
        "created_at",
        "created_by",
    )
