from .base import *  # noqa: F403


SECRET_KEY = "test-key-that-is-long-enough-and-never-used-in-production"
DEBUG = False
ALLOWED_HOSTS = ["testserver"]
SURNAS_DEMO_MODE = True
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
DATABASES[SURNAS_DB_ALIAS] = {  # noqa: F405
    "ENGINE": "django.db.backends.sqlite3",
    "NAME": ":memory:",
}
