import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("SECRET_KEY", "django-insecure-dev-only")
# The API is only reached through the web app's proxy, never directly by browsers.
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "workspace",
    "reviews",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": dj_database_url.config(default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
}
if DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3":
    DATABASES["default"]["OPTIONS"] = {
        # Writers take the lock at BEGIN, so a request's check-then-insert is serialized.
        "transaction_mode": "IMMEDIATE",
        "timeout": 20,
        "init_command": "PRAGMA journal_mode=WAL;",
    }
    # A file, not the default in-memory database, so concurrency tests use real locking.
    DATABASES["default"]["TEST"] = {"NAME": str(BASE_DIR / "test_db.sqlite3")}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

TIME_ZONE = "UTC"
USE_TZ = True

PLAN_LIMIT = int(os.environ.get("PLAN_LIMIT", "10"))
REVIEW_TIMEOUT_S = int(os.environ.get("REVIEW_TIMEOUT_S", "60"))
PLAN_TZ = os.environ.get("PLAN_TZ", "Europe/Rome")

SAMPLES_DIR = Path(os.environ.get("SAMPLES_DIR", BASE_DIR.parent / "samples"))
