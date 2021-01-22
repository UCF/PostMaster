import os


DEBUG = True
LOCAL_DEBUG = False
ADMINS = (
    #('Your Name', 'your_email@domain.com'),
)

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
# MEDIA_URL = '/static/'

# Base URL of the project. Needed in places where build_absolute_uri
# can't be used because there is no request object (e.g. management commands)
# No trailing slash
PROJECT_URL = 'http://127.0.0.1:8000'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

LOGIN_URL = '/login'
LOGOUT_URL = '/logout'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'whatisthisnonsense?'

DATABASES = {
    'default': {
        # postgresql_psycopg2, postgresql, mysql, sqlite3, oracle
        'ENGINE'  : 'django.db.backends.sqlite3',
        # Or path to database file if using sqlite3.
        'NAME'    : 'postmaster.db',
        # Not used with sqlite3.
        'USER'    : '',
        # Not used with sqlite3.
        'PASSWORD': '',
        # Set to empty string for localhost. Not used with sqlite3.
        'HOST'    : '',
        # Set to empty string for default. Not used with sqlite3.
        'PORT'    : '',
    },
    # Currently on the database name needs to be filled in for the rds_warehouse
    # database. It is only used in the recipient-importer script.
    'rds_wharehouse': {
        # postgresql_psycopg2, postgresql, mysql, sqlite3, oracle
        'ENGINE'  : 'django.db.backends.sqlite3',
        # Or path to database file if using sqlite3.
        'NAME'    : 'rds_wharehousedev',
        # Not used with sqlite3.
        'USER'    : '',
        # Not used with sqlite3.
        'PASSWORD': '',
        # Set to empty string for localhost. Not used with sqlite3.
        'HOST'    : '',
        # Set to empty string for default. Not used with sqlite3.
        'PORT'    : '',
    }
}

AMAZON_SMTP = {
    'host'    : 'email-smtp.us-east-1.amazonaws.com',
    'port'    : 465,
    'username': '',
    'password': '',
    'quota'   : 500000, # per 24 hours
    'rate'    : 70 # per second
}

AMAZON_S3 = {
    'aws_access_key_id': '',
    'aws_secret_access_key': '',
    'bucket': '',  # this bucket must have CORS enabled
    'base_key_path': '', # optional; prefixes keys with some directory
    'valid_extension_groups': {
        # Defines sets of valid filetypes by name
        'image': ['.png', '.jpg', '.jpeg', '.gif'],
        'html': ['.html'],
        'plaintext': ['.txt']
    }
}


# NET Domain LDAP CONFIG
LDAP_NET_HOST        = 'ldaps://net.ucf.edu'
LDAP_NET_BASE_DN     = 'ou=People,dc=net,dc=ucf,dc=edu'
LDAP_NET_USER_SUFFIX = '@net.ucf.edu'
LDAP_NET_ATTR_MAP    = { # LDAP Object -> User Object
    'givenName': 'first_name',
    'sn': 'sn',
    'mail': 'email'
}
LDAP_NET_SEARCH_USER = ''
LDAP_NET_SEARCH_PASS = ''
LDAP_NET_SEARCH_SIZELIMIT = 5

# NID of users who are allowed to manage Postmaster. Tuple format ('NID', 'NID1', 'NID2')
MANAGERS = ()

# Set to TRUE when operating over SSL
SESSION_COOKIE_SECURE = True

# How often is the email processing script set to run? In seconds
PROCESSING_INTERVAL_DURATION = (60 * 14) + 59 # 14:59 seconds - 15 minutes because of zeroith second

# How long before an email is sent with the previews be sent?
PREVIEW_LEAD_TIME  = 60 * 60 # 1 hour

# Determines the minimum number of emails that should exist before importing them
MINIMUM_IMPORT_EMAIL_COUNT = 1000

# Email address that test emails will be sent to. See manager/tests.py
TEST_EMAIL_RECIPIENT = ''

# Source URIs that test emails will use
TEST_EMAIL_SOURCE_HTML_URI = ''
TEST_EMAIL_SOURCE_TEXT_URI = ''

STATIC_URL = '/static/'
# STATIC_ROOT = os.path.join(BASE_DIR, "static") # Comment out when using locally
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static")
]

UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        }
    },
    'formatters': {
        'talkative': {
            'format': '[%(asctime)s] %(levelname)s:%(module)s %(funcName)s %(lineno)d %(message)s'
        },
        'concise': {
            'format': '%(levelname)s: %(message)s (%(asctime)s)'
        }
    },
    'handlers': {
        'discard': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler'
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'talkative',
            'filters': ['require_debug_true']
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'application.log'),
            'formatter': 'talkative',
            'filters': ['require_debug_false']
        }
    },
    'loggers': {
        'core': {
            'handlers': ['console', 'file'],
            'propogate': True,
            'level': 'WARNING'
        },
        'django': {
            'handlers': ['console', 'file'],
            'propogate': True,
            'level': 'WARNING'
        },
        'events': {
            'handlers': ['console', 'file'],
            'propogate': True,
            'level': 'WARNING'
        },
        'profiles': {
            'handlers': ['console', 'file'],
            'propogate': True,
            'level': 'WARNING'
        },
        'util': {
            'handlers': ['console', 'file'],
            'level': 'WARNING'
        }
    }
}

DATADOG_CONFIG = {
    # The service to use when reporting stats to datadog.
    # Valid options are `statsd` or `api`.
    'service': 'statsd',
    'statsd': {
        'host': None, # The host of the statsd service.
        'port': None  # The port of the statsd service.
    },
    'api': {
        'api_key': None, # The API key to use for the datadog API.
        'app_key': None  # The app key to use when reporting datadog stats to the API.
    },
    'tags': [
        'env:{environment}', # Replace with the environment
        'fn:web', # Function of the service
        'loc:{location}', # DSO or wherever
        'stack:{eduapp or whatevs}' # The particular stack this is running on.
    ]
}
