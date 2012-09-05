
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
	'manager',
)

AUTHENTICATION_BACKENDS = (
	'manager.auth.Backend',
)

LOGGING = {
	'version':1,
	'disable_existing_loggers':True,
	'filters': {
		'require_debug_true': {
			'()': 'logs.RequiredDebugTrue',
		},
		'require_debug_false': {
			'()': 'logs.RequiredDebugFalse',
		}
	},
	'formatters': {
		'talkative': {
			'format':'[%(asctime)s]%(levelname)s:%(module)s:%(funcName)s:%(lineno)d:%(message)s'
		},
		'concise': {
			'format':'%(levelname)s: %(message)s (%(asctime)s)'
		}
	},
	'handlers': {
		'discard': {
			'level':'DEBUG',
			'class':'django.utils.log.NullHandler'
		},
		'console': {
			'level':'DEBUG',
			'class':'logging.StreamHandler',
			'formatter':'talkative',
			'filters': ['require_debug_true']
		},
		'file': {
			'level': 'INFO',
			'class':'logging.FileHandler',
			'filename': os.path.join(PROJECT_FOLDER,'logs', 'application.log'),
			'formatter':'concise',
			'filters': ['require_debug_false']
		},
		'nteventlog': {
			'level'  : 'INFO',
			'class'  : 'logging.handlers.NTEventLogHandler',
			'appname': 'postmaster',
			'filters': ['require_debug_false']
		}
	},
	'loggers': {
		'django': {
			'handlers':['discard'],
			'propogate': True,
			'level':'INFO'
		},
		'manager': {
			'handlers':['console', 'file'],
			'propogate': True,
			'level':'DEBUG'
		},
	}
}

MESSAGE_TAGS = {
	message_constants.DEBUG   : '',
	message_constants.INFO    : 'alert-info',
	message_constants.SUCCESS : 'alert-success',
	message_constants.WARNING : 'alert-error',
	message_constants.ERROR   : 'alert-error',
}

DOT = ''
with open(os.path.join(PROJECT_FOLDER, 'static', 'img', 'dot.png'), 'r') as dot:
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
