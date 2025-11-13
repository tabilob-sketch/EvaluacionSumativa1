"""
Django settings for config project.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# ===================================
# BASE DIR
# ===================================
BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar variables de entorno
load_dotenv(BASE_DIR / ".env")

# ===================================
# CONFIG BÁSICA
# ===================================

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-unsafe")

DEBUG = os.getenv("DJANGO_DEBUG", "True") == "True"

ALLOWED_HOSTS = os.getenv(
    "DJANGO_ALLOWED_HOSTS",
    "127.0.0.1,localhost,3.215.158.126"
).split(",")

CSRF_TRUSTED_ORIGINS = os.getenv(
    "DJANGO_CSRF_TRUSTED_ORIGINS",
    "http://3.215.158.126"
).split(",")

# ===================================
# APPS INSTALADAS
# ===================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # APP PRINCIPAL
    "core.apps.CoreConfig",
]

# ===================================
# MIDDLEWARE
# ===================================

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

# ===================================
# TEMPLATES
# ===================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

# ===================================
# BASE DE DATOS
# ===================================

DB_ENGINE = os.getenv("DB_ENGINE", "sqlite")

if DB_ENGINE == "mysql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.getenv("DB_NAME"),
            "USER": os.getenv("DB_USER"),
            "PASSWORD": os.getenv("DB_PASSWORD"),
            "HOST": os.getenv("DB_HOST", "127.0.0.1"),
            "PORT": os.getenv("DB_PORT", "3306"),
            "OPTIONS": {"charset": "utf8mb4"},
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# ===================================
# VALIDADORES DE CONTRASEÑA
# ===================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"
    },
]

# ===================================
# INTERNACIONALIZACIÓN
# ===================================

LANGUAGE_CODE = os.getenv("DJANGO_LANGUAGE_CODE", "es-cl")

TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "America/Santiago")

USE_I18N = True
USE_TZ = True

# ===================================
# STATIC & MEDIA
# ===================================

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ===================================
# DEFAULT PRIMARY KEY
# ===================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ===================================
# LOGIN / LOGOUT
# ===================================

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"
