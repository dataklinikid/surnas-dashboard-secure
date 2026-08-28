from django.contrib import admin

from .models import SurveyAccess, SurveyMembership


class SurveyMembershipInline(admin.TabularInline):
    model = SurveyMembership
    extra = 0


@admin.register(SurveyAccess)
class SurveyAccessAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "active")
    list_filter = ("active",)
    search_fields = ("code", "name")
    inlines = (SurveyMembershipInline,)


@admin.register(SurveyMembership)
class SurveyMembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "survey", "can_monitor", "can_analyse", "can_export")
    list_filter = ("survey", "can_monitor", "can_analyse", "can_export")
    search_fields = ("user__username", "survey__code", "survey__name")
