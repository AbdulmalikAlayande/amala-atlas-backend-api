from pathlib import Path

from amala_atlas.environment import ENV

import dj_database_url
import os


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = ENV.str("SECRET_KEY")
#'9+byr)yf$a&y8!orrt)^mvj2ar$m4=6s*zxai)s+42o9oz1nb_'

DEBUG = ENV.bool("DEBUG", "False")

# ALLOWED_HOSTS = []
ALLOWED_HOSTS = ["amala-atlas.onrender.com", "localhost", "127.0.0.1"]
CORS_ALLOWED_ORIGINS = ENV.str(
    "CORS_ALLOWED_ORIGINS", "http://localhost:3000,https://amalaatlas-hazel.vercel.app"
).split(",")
CSRF_TRUSTED_ORIGINS = ENV.str(
    "CSRF_TRUSTED_ORIGINS", "http://localhost:3000,https://amalaatlas-hazel.vercel.app"
).split(",")

# Ingestion API key for automated discovery agents
INGEST_API_KEY = ENV.str("INGEST_API_KEY", "dev-ingest-key")

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "commons.apps.CommonsConfig",
    "ingestion.apps.IngestionConfig",
    "media.apps.MediaConfig",
    "places.apps.PlacesConfig",
    "users.apps.UsersConfig",
    "verification.apps.VerificationConfig",
    "whatsapp.apps.WhatsappConfig",
    "django_extensions.apps.DjangoExtensionsConfig",
    "django_filters",
    "rest_framework.apps.RestFrameworkConfig",
    "corsheaders",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "amala_atlas.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "amala_atlas.wsgi.application"


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }
DATABASES = {"default": dj_database_url.config(default=os.environ.get("DATABASE_URL"))}

AUTH_USER_MODEL = "users.User"
# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "EXCEPTION_HANDLER": "rest_framework_json_api.exceptions.exception_handler",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
    ],
    "DEFAULT_METADATA_CLASS": "rest_framework_json_api.metadata.JSONAPIMetadata",
    "DEFAULT_FILTER_BACKENDS": (
        "rest_framework_json_api.filters.QueryParameterValidationFilter",
        "rest_framework_json_api.filters.OrderingFilter",
        "rest_framework_json_api.django_filters.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
    ),
    "SEARCH_PARAM": "filter[search]",
    "TEST_REQUEST_RENDERER_CLASSES": (
        "rest_framework_json_api.renderers.JSONRenderer",
    ),
    "TEST_REQUEST_DEFAULT_FORMAT": "vnd.api+json",
}

# WhatsApp / Twilio configuration
TWILIO_ACCOUNT_SID = ENV.str("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = ENV.str("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_NUMBER = ENV.str("TWILIO_WHATSAPP_NUMBER", "")

# Agentic discovery API keys
GOOGLE_MAPS_API_KEY = ENV.str("GOOGLE_MAPS_API_KEY", "")
TWITTER_BEARER_TOKEN = ENV.str("TWITTER_BEARER_TOKEN", "")
