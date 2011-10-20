import os
import sys

third_party_dir = os.path.join(os.path.dirname(__file__), 'third-party')
sys.path.append(os.path.realpath(third_party_dir))

ADMINS = ()
DEBUG = True
INSTALLED_APPS = ()
LANGUAGE_CODE = 'en-us'
MANAGERS = ADMINS
MIDDLEWARE_CLASSES = ()
ROOT_URLCONF = 'urls'
SITE_ID = 1
TEMPLATE_DEBUG = DEBUG
TIME_ZONE = 'America/New_York'
USE_I18N = False
USE_L10N = False

CACHES = {
    'default': {
      'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
      'LOCATION': 'django_cache',
    }
  }

INSTALLED_APPS = (
    'clean',
    'train',
    'debug_toolbar',
    )

STATIC_ROOT = ''
STATIC_URL = '/static/'
STATICFILES_DIRS = (
    os.path.join(os.path.dirname(__file__), 'static'),
    )
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    )

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    )
TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(__file__), 'templates'),
    )

# Override above with local settings.
from settings_local import *  #@UnusedWildImport
