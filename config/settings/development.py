from .base import *  # noqa: F403


DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
SURNAS_DEMO_MODE = True

# Alias tersedia agar router tetap dapat diperiksa tanpa server MariaDB.
DATABASES[SURNAS_DB_ALIAS] = {  # noqa: F405
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": BASE_DIR / "survey_demo.sqlite3",  # noqa: F405
}
