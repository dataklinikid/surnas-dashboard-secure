from django.urls import path

from . import views


app_name = "aggregate"

urlpatterns = [
    path("", views.home, name="home"),
    path("manage/sources/", views.source_catalog, name="source_catalog"),
    path("manage/sources/link/", views.source_catalog_link, name="source_catalog_link"),
    path(
        "manage/events/new/",
        views.event_onboarding_identity,
        name="event_onboarding_identity",
    ),
    path(
        "manage/events/new/references/",
        views.event_onboarding_references,
        name="event_onboarding_references",
    ),
    path(
        "manage/events/new/modules/",
        views.event_onboarding_modules,
        name="event_onboarding_modules",
    ),
    path(
        "manage/events/new/source/",
        views.event_onboarding_source,
        name="event_onboarding_source",
    ),
    path(
        "manage/events/new/review/",
        views.event_onboarding_review,
        name="event_onboarding_review",
    ),
    path(
        "manage/events/new/done/<slug:survey_code>/",
        views.event_onboarding_done,
        name="event_onboarding_done",
    ),
    path(
        "manage/events/<slug:survey_code>/metadata/",
        views.event_metadata_setup,
        name="event_metadata_setup",
    ),
    path(
        "manage/events/<slug:survey_code>/validation/",
        views.event_final_validation,
        name="event_final_validation",
    ),
    path(
        "manage/events/<slug:survey_code>/psu-frame/",
        views.event_psu_frame_setup,
        name="event_psu_frame_setup",
    ),
    path(
        "manage/events/<slug:survey_code>/weighting/",
        views.event_weighting_setup,
        name="event_weighting_setup",
    ),
    path(
        "manage/events/<slug:survey_code>/activate/",
        views.event_activation_review,
        name="event_activation_review",
    ),
    path(
        "manage/events/new/cancel/",
        views.event_onboarding_cancel,
        name="event_onboarding_cancel",
    ),
    path("healthz/", views.healthz, name="healthz"),
]
