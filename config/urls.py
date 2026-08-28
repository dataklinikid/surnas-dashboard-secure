from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("surveys/<slug:survey_code>/", include("surnasdes26.generic_urls", namespace="surveys")),
    path("surnasdes26/", include("surnasdes26.urls")),
    path("", include("aggregate.urls")),
]
