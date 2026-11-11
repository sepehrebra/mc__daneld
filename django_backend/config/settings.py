import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "development-only-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"
ALLOWED_HOSTS = [host.strip() for host in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if host.strip()]

INSTALLED_APPS = ["django.contrib.contenttypes", "rest_framework", "corsheaders", "accounts", "farms", "operations"]
MIDDLEWARE = ["corsheaders.middleware.CorsMiddleware", "django.middleware.common.CommonMiddleware"]
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": os.environ.get("DJANGO_DATABASE_PATH", str(BASE_DIR / "django.sqlite3"))}}
TIME_ZONE = "UTC"
USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
try:
    SESSION_TTL_HOURS = int(os.environ.get("SESSION_TTL_HOURS", "24"))
    if not 1 <= SESSION_TTL_HOURS <= 720:
        raise ValueError
except ValueError as exc:
    raise ImproperlyConfigured("SESSION_TTL_HOURS must be an integer between 1 and 720.") from exc
PASSWORD_HASHERS = ["django.contrib.auth.hashers.Argon2PasswordHasher"]
CORS_ALLOWED_ORIGINS = list(dict.fromkeys(["http://localhost:5173"] + [origin.strip() for origin in os.environ.get("CORS_ORIGINS", "").split(",") if origin.strip()]))
CORS_ALLOW_METHODS = ("GET", "POST", "PATCH", "DELETE", "OPTIONS")
CORS_ALLOW_HEADERS = ("authorization", "content-type")
REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "config.errors.exception_handler",
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_AUTHENTICATION_CLASSES": ["accounts.authentication.BearerAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
}
