"""
Django settings for kissan project (Render deployment ready).
"""

from pathlib import Path
import os
import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG=True
# ----------------------------
# SECURITY SETTINGS
# ----------------------------

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-f!h(#71a15ms5*rp2@ysmmc4(l#q_w8k8+!7g9ama^0%1tpg@o"  # fallback (for local dev)
)

DEBUG = True

# Render provides your custom domain automatically
ALLOWED_HOSTS = ["localhost", "127.0.0.1", ".onrender.com"]

# ----------------------------
# AUTH SETTINGS
# ----------------------------

AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "/accounts/auth/"
LOGIN_REDIRECT_URL = "/core/dashboard/"

AUTHENTICATION_BACKENDS = [
    "accounts.backends.MobileBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# ----------------------------
# APPLICATIONS
# ----------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # your apps
    "accounts",
    "core",
    "ai",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # for static files
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "kissan.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "kissan.wsgi.application"

# ----------------------------
# DATABASE CONFIG
# ----------------------------

DATABASES = {
    "default": dj_database_url.config(
        default="postgresql://neondb_owner:npg_9rtRMYluj6WU@ep-orange-dust-adimf7yy-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require",
        conn_max_age=600,
        ssl_require=True,
    )
}

# ----------------------------
# PASSWORD VALIDATION
# ----------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ----------------------------
# INTERNATIONALIZATION
# ----------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ----------------------------
# STATIC FILES
# ----------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# Whitenoise settings
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# ----------------------------
# DEFAULT PRIMARY KEY
# ----------------------------

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
