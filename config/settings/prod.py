# config/settings/prod.py
import os
import dj_database_url
from .base import *  # noqa

DEBUG = False

# alwaysdata gives you a *.alwaysdata.net subdomain; set this in .env
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "").split(",")

# CSRF needs the full https origin in production
CSRF_TRUSTED_ORIGINS = [
    f"https://{host}" for host in ALLOWED_HOSTS if host
]

# Postgres — alwaysdata provides a DATABASE_URL in the panel
DATABASES = {
    "default": dj_database_url.parse(os.environ["DATABASE_URL"], conn_max_age=600)
}

# Force HTTPS cookies. alwaysdata terminates SSL for you.
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Security hardening
SECURE_HSTS_SECONDS = 31536000          # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Static files — WhiteNoise reads from this folder after `collectstatic`
STATIC_ROOT = BASE_DIR / "staticfiles"