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

MIDDLEWARE = [
]

ROOT_URLCONF = 'readability.urls'

TEMPLATES = [{
  'BACKEND': 'django.template.backends.django.DjangoTemplates',
  'DIRS': [],
  'APP_DIRS': True,
}]

WSGI_APPLICATION = 'wsgi.application'
