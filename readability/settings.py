"""Django settings for Readability API project.

--------------------------------------------------------------------------------

Readability API - Clean up pages and feeds to be readable.
Copyright (C) 2010  Anthony Lieuallen

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
import datetime
import os
from pathlib import Path

DB_DIR = Path(__file__).parent.parent.resolve()

SECRET_KEY = os.getenv(
  'SECRET_KEY', default='!j9s1*ama_q1e@!fm2cn@*r#^%5aoq&$x-x&swwq3ys$1*ta17')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = bool(os.getenv('DEBUG'))

ALLOWED_HOSTS = []

DATABASES = {
  'default': {
    'ENGINE': 'django.db.backends.sqlite3',
    'NAME': DB_DIR / 'readability.db',
  }
}

HUEY = {
  #'huey_class': 'huey.SqliteHuey',
  #'filename': DB_DIR / 'huey.db',
  # MiniHuey ?
  'huey_class': 'huey.MemoryHuey',
}

INSTALLED_APPS = [
  'readability',
  'huey.contrib.djhuey',
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
        location=str(DB_DIR / 'requests_cache.db'), extension=''),
    expire_after=datetime.timedelta(hours=23))
