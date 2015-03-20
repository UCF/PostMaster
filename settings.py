
# Django settings for generic project.
import os
import sys
from django.contrib.messages import constants as message_constants

PROJECT_FOLDER    = os.path.dirname(os.path.abspath(__file__))
APP_FOLDER        = os.path.join(PROJECT_FOLDER, 'apps')
INC_FOLDER        = os.path.join(PROJECT_FOLDER, 'third-party')
ROOT_URLCONF      = os.path.basename(PROJECT_FOLDER) + '.urls'

TIME_ZONE         = 'America/New_York'
LANGUAGE_CODE     = 'en-us'
SITE_ID           = 1
USE_I18N          = False

LOGIN_REDIRECT_URL = '/'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.request",
    'django.contrib.messages.context_processors.messages',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

# Add local apps folder to python path
sys.path.append(APP_FOLDER)
sys.path.append(INC_FOLDER)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'widget_tweaks',
    'manager',
)

AUTHENTICATION_BACKENDS = (
    'manager.auth.Backend',
)

MESSAGE_TAGS = {
    message_constants.DEBUG   : '',
    message_constants.INFO    : 'alert-info',
    message_constants.SUCCESS : 'alert-success',
    message_constants.WARNING : 'alert-danger',
    message_constants.ERROR   : 'alert-danger',
}

DOT = ''
with open(os.path.join(PROJECT_FOLDER, 'static', 'img', 'dot.png'), 'rb') as dot:
    DOT = dot.read()

try:
    from settings_local import *
except ImportError:
    from django.core.exceptions import ImproperlyConfigured
    raise ImproperlyConfigured(
        'Local settings file was not found. ' +
        'Ensure settings_local.py exists in project root.'
    )


TEMPLATE_DEBUG = DEBUG
TEMPL_FOLDER   = os.path.join(PROJECT_FOLDER, 'templates')
MEDIA_ROOT     = os.path.join(PROJECT_FOLDER, 'static')
TEMPLATE_DIRS  = (TEMPL_FOLDER,)
