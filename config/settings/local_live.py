import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv


_ENV_FILE = Path(__file__).resolve().parents[2] / ".env.local"
if not _ENV_FILE.is_file():
    raise ImproperlyConfigured(
        "File .env.local tidak ditemukan. Salin .env.local.example menjadi .env.local."
    )
load_dotenv(_ENV_FILE)

from .base import *  # noqa: E402,F403


DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]
SURNAS_DEMO_MODE = False
SURNAS_LEGACY_SOURCE = True
