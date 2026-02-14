import json
import os
from pathlib import Path

from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')
DEBUG = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1,web', cast=Csv())

# Django apps
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

# Third party apps
INSTALLED_APPS += [
    'corsheaders',
    'django_prometheus',
    'django_celery_beat',
]

# Local apps
INSTALLED_APPS += [
    'apps.devices',
    'apps.users',
    'apps.rules',
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'conf.middleware.logging_middleware.LoggingMiddleware',  # Logging middleware
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'conf.middleware.rate_limit.RateLimitMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

ROOT_URLCONF = 'conf.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'conf.wsgi.application'

# Databases
IS_BUILD = os.environ.get('BUILD_TIME') == '1'

if IS_BUILD:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": "/tmp/db.sqlite3",
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME'),
            'USER': config('DB_USER'),
            'PASSWORD': config('DB_PASSWORD'),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432', cast=int),
        },
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTH_USER_MODEL = 'users.User'

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CORS_ALLOW_ALL_ORIGINS = config(
    'CORS_ALLOW_ALL_ORIGINS',
    default=False,
    cast=bool
)

CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='',
    cast=lambda v: v.split(',') if v else []
)

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_ALL_ORIGINS = config('CORS_ALLOW_ALL_ORIGINS', default=False, cast=bool)

CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000,http://localhost:5173',
    cast=Csv()
)

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# Rate limit: load from env JSON for scalability; defaults preserved when RATE_LIMIT_CONFIG_JSON unset
_DEFAULT_RATE_LIMIT_CONFIG = {
    "enabled": True,
    "trusted_proxies": ["127.0.0.1/32", "10.0.0.0/8"],
    "response": {"code": 429, "message": "Too many requests"},
    "rules": {
        "/api/login/": {"limit": 10, "window": 60},
        "/api/": {"limit": 100, "window": 60},
    },
}
_raw = os.environ.get("RATE_LIMIT_CONFIG_JSON") or "{}"
try:
    _env_config = json.loads(_raw) if isinstance(_raw, str) else _raw
except (json.JSONDecodeError, TypeError):
    _env_config = {}
RATE_LIMIT_CONFIG = {
    **_DEFAULT_RATE_LIMIT_CONFIG,
    **_env_config,
    "rules": {
        **_DEFAULT_RATE_LIMIT_CONFIG.get("rules", {}),
        **(_env_config.get("rules") or {}),
    },
}
RATE_LIMIT_ENABLED = RATE_LIMIT_CONFIG.get("enabled", True)
RATE_LIMIT_TRUSTED_PROXIES = RATE_LIMIT_CONFIG.get("trusted_proxies", _DEFAULT_RATE_LIMIT_CONFIG["trusted_proxies"])
RATE_LIMIT_RESPONSE = RATE_LIMIT_CONFIG.get("response", _DEFAULT_RATE_LIMIT_CONFIG["response"])
RATE_LIMIT_RULES = RATE_LIMIT_CONFIG.get("rules", _DEFAULT_RATE_LIMIT_CONFIG["rules"])

# Celery configuration
if USE_TZ:
    CELERY_TIMEZONE = TIME_ZONE

CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://127.0.0.1:6379/0')

CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

CELERY_TASK_ACKS_LATE = True
CELERY_TASK_SEND_SENT_EVENT = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_TASK_TIME_LIMIT = 2 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 60
CELERY_TASK_DEFAULT_RETRY_DELAY = 5
CELERY_TASK_MAX_RETRIES = 10

CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_RESULT_EXPIRES = 60 * 60

# scheduler conf
CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

# LOGGING configuration for django and celery
DJANGO_LOG_LEVEL = config('DJANGO_LOG_LEVEL', default='INFO')
CELERY_LOG_LEVEL = config('CELERY_LOG_LEVEL', default='INFO')
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": 'pythonjsonlogger.jsonlogger.JsonFormatter',
            "format": "{asctime} {levelname} {name} {message} {request_id} {duration}",
            "style": "{",
            "rename_fields": {
                "asctime": "timestamp",
                "levelname": "level",
                "name": "logger_name",
            },
        },

        "celery_json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "{asctime} {levelname} {name} {message} {task_id} {task_name}",
            "style": "{",
            "rename_fields": {
                "asctime": "timestamp",
                "levelname": "level",
                "name": "logger_name",
            },
        },
    },

    "filters": {
        "request_context": {
            "()": "conf.filters.logging_filters.RequestContextFilter",
        },
        "celery_context": {
            "()": "conf.filters.logging_filters.CeleryContextFilter",
        },
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["request_context"],
            "formatter": "json",
        },

        "celery_console": {
            "class": "logging.StreamHandler",
            "filters": ["celery_context"],
            "formatter": "celery_json",
        },
    },

    "loggers": {
        "": {
            "handlers": ["console"],
            "level": DJANGO_LOG_LEVEL,
        },

        "django": {  # Django logger is declared (propagate = False by default)
            "handlers": ["console"],
            "level": DJANGO_LOG_LEVEL,
            "propagate": False,
        },

        "celery": {
            "handlers": ["celery_console"],
            "level": CELERY_LOG_LEVEL,
            "propagate": False,
        },
    },
}

TELEMETRY_ASYNC_HEADER = 'Ingest-Async'
TELEMETRY_ASYNC_BATCH_THRESHOLD = config(
    'TELEMETRY_ASYNC_BATCH_THRESHOLD',
    default='50',
    cast=int
)
