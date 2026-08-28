from django.urls import path

from . import views


app_name = "surnasdes26"

urlpatterns = [
    path("monitoring/", views.monitoring, {"survey_code": "surnasfeb26"}, name="monitoring"),
    path("analysis/", views.analysis, {"survey_code": "surnasfeb26"}, name="analysis"),
    path("crosstab/", views.crosstab, {"survey_code": "surnasfeb26"}, name="crosstab"),
    path("multiple-answer/", views.multiple_answer, {"survey_code": "surnasfeb26"}, name="multiple_answer"),
    path("api/frequency.json", views.frequency_api, {"survey_code": "surnasfeb26"}, name="frequency_api"),
]
