import environ

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
        # Use 'REDIS_URL' from docker-compose, or fallback to default
        "LOCATION": env("REDIS_URL", default="redis://redis:6379/0"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}
