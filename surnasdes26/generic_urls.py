from django.urls import path

from . import views


app_name = "surveys"

urlpatterns = [
    path("monitoring/", views.monitoring, name="monitoring"),
    path("analysis/", views.analysis, name="analysis"),
    path("crosstab/", views.crosstab, name="crosstab"),
    path("multiple-answer/", views.multiple_answer, name="multiple_answer"),
    path("api/frequency.json", views.frequency_api, name="frequency_api"),
]
