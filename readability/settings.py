import datetime
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()

SECRET_KEY = os.getenv(
  'SECRET_KEY', default='!j9s1*ama_q1e@!fm2cn@*r#^%5aoq&$x-x&swwq3ys$1*ta17')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = bool(os.getenv('DEBUG'))

ALLOWED_HOSTS = []

DATABASES = {
  'default': {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': BASE_DIR / 'db',
  }
}

INSTALLED_APPS = [
  'readability'
]

LOGGING = {
  'version': 1,
  'disable_existing_loggers': False,
  'handlers': {
    'console': {'class': 'logging.StreamHandler'},
  },
  'root': {
    'handlers': ['console'],
    'level': 'DEBUG',
  }
}

MIDDLEWARE = [
]

ROOT_URLCONF = 'readability.urls'

TEMPLATES = [{
  'BACKEND': 'django.template.backends.django.DjangoTemplates',
  'DIRS': [],
  'APP_DIRS': True,
}]

WSGI_APPLICATION = 'wsgi.application'


import requests_cache
requests_cache.install_cache(
    backend=requests_cache.backends.sqlite.DbCache(
        location=str(BASE_DIR / 'db'), extension=''),
    expire_after=datetime.timedelta(hours=23))
