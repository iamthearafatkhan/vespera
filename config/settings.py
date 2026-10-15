# config/settings.py
from pathlib import Path
import os
from dotenv import load_dotenv

# BASE_DIR = the folder that contains manage.py
BASE_DIR = Path(__file__).resolve().parent.parent

# load variables from .env into os.environ
load_dotenv(BASE_DIR / ".env")

# ---- Core security ----
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-only-insecure-key")
DEBUG = os.getenv("DJANGO_DEBUG", "True") == "True"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# ---- Apps ----
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # our app
    "accounts",
    "courses",
    'expenses',
    'routines',
    "dashboard",
    "analytics_app",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],   # project-wide templates folder
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---- Database ----
# SQLite for development. We'll switch to Postgres on alwaysdata in Phase 7.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ---- Password policy ----
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    # our custom one — enforces uppercase + lowercase + digit
    {"NAME": "accounts.validators.ComplexityValidator"},
]

# Use Argon2 first (strongest). Requires `argon2-cffi` in requirements.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

# ---- i18n ----
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Dhaka"        # change if you're elsewhere
USE_I18N = True
USE_TZ = True

# ---- Static & media ----
STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"      # used only by `collectstatic` in prod

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---- Auth redirects ----
AUTH_USER_MODEL = "accounts.User"           # MUST be set before first migration
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:profile"
LOGOUT_REDIRECT_URL = "accounts:login"

# ---- Security (dev-friendly, tighten in prod) ----
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False                # JS needs to read this for HTMX later
X_FRAME_OPTIONS = "DENY"