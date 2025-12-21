import environ
from celery.schedules import crontab

from .base import *  # Import defaults from base.py

# Initialize environment variables
env = environ.Env()

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY", default="django-insecure-dev-key")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ["*"]

# Database
# 'env.db()' automatically parses the 'DATABASE_URL' from docker-compose.yml
# e.g., postgres://postgres:postgres@db:5432/loyalty_db
DATABASES = {
    "default": env.db(),
}

# Redis Cache
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://redis:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

# --- CELERY SETTINGS ---
CELERY_BROKER_URL = env("REDIS_URL", default="redis://redis:6379/0")
CELERY_RESULT_BACKEND = env("REDIS_URL", default="redis://redis:6379/0")

CELERY_ACCEPT_CONTENT = ["application/json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
# Ensure TIME_ZONE is defined in base.py, otherwise set it here, e.g., 'UTC'
CELERY_TIMEZONE = TIME_ZONE


CELERY_BEAT_SCHEDULE = {
    "expire_old_points_yearly": {
        "task": "loyalty.tasks.process_yearly_points_expiration",
        # Run at 00:30 on January 1st
        "schedule": crontab(minute=30, hour=0, day_of_month=1, month_of_year=1),
    },
}
