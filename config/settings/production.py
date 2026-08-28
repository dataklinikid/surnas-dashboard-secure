import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403


def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"Environment variable {name} wajib diisi.")
    return value


SECRET_KEY = required("DJANGO_SECRET_KEY")
if len(SECRET_KEY) < 50:
    raise ImproperlyConfigured("DJANGO_SECRET_KEY minimal 50 karakter.")

DEBUG = False
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")  # noqa: F405
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS wajib diisi.")

CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")  # noqa: F405
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)  # noqa: F405
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool("DJANGO_HSTS_INCLUDE_SUBDOMAINS", True)  # noqa: F405
SECURE_HSTS_PRELOAD = env_bool("DJANGO_HSTS_PRELOAD", False)  # noqa: F405
SECURE_REFERRER_POLICY = "same-origin"

if env_bool("DJANGO_BEHIND_HTTPS_PROXY", False):  # noqa: F405
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": required("DJANGO_DB_NAME"),
        "USER": required("DJANGO_DB_USER"),
        "PASSWORD": required("DJANGO_DB_PASSWORD"),
        "HOST": required("DJANGO_DB_HOST"),
        "PORT": os.getenv("DJANGO_DB_PORT", "5432").strip(),
        "CONN_MAX_AGE": int(os.getenv("DJANGO_DB_CONN_MAX_AGE", "60")),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {
            "connect_timeout": int(os.getenv("DJANGO_DB_CONNECT_TIMEOUT", "10")),
            "sslmode": os.getenv("DJANGO_DB_SSLMODE", "prefer").strip(),
        },
    }
}

SURNAS_DEMO_MODE = False
SURNAS_LEGACY_SOURCE = True
