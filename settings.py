import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve()

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
  #'django.contrib.admin',
  #'django.contrib.auth',
  #'django.contrib.contenttypes',
  #'django.contrib.sessions',
  #'django.contrib.messages',
  #'django.contrib.staticfiles',
]

MIDDLEWARE = [
  #'django.middleware.security.SecurityMiddleware',
  #'django.contrib.sessions.middleware.SessionMiddleware',
  #'django.middleware.common.CommonMiddleware',
  #'django.middleware.csrf.CsrfViewMiddleware',
  #'django.contrib.auth.middleware.AuthenticationMiddleware',
  #'django.contrib.messages.middleware.MessageMiddleware',
  #'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'urls'

TEMPLATES = [{
  'BACKEND': 'django.template.backends.django.DjangoTemplates',
  'DIRS': [],
  'APP_DIRS': True,
  'OPTIONS': {
    'context_processors': [
      #'django.template.context_processors.debug',
      #'django.template.context_processors.request',
      #'django.contrib.auth.context_processors.auth',
    ],
  },
}]

WSGI_APPLICATION = 'wsgi.application'
