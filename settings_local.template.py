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
PROJECT_FOLDER = os.path.dirname(os.path.abspath(__file__))

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
        'html': ['.html']
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
# STATIC_ROOT = os.path.join(PROJECT_FOLDER, "static") # Comment out when using locally
STATICFILES_DIRS = [
    os.path.join(PROJECT_FOLDER, "static")
]

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
        # To log to the Windows event log instead of application.log, change the
        # `file` in the line `nteventlog` in the `handlers` line below
        'manager': {
            'handlers':['console', 'file'],
            'propogate': True,
            'level':'DEBUG'
        },
    }
}

LITMUS_USER = 'user'
LITMUS_PASS = 'pass'
LITMUS_BASE_URL = 'https://ucf.litmus.com/'
# SNI is not native to python 2.6.6. The link below indicates options that
# don't seem to work. Python 2.6.6 with pyOpenSSL causes a
# "data must be a byte string" error. Sugget using python 2.7.9 or later
# which has native SNI.
# http://stackoverflow.com/questions/29134512/insecureplatformwarning-a-true-sslcontext-object-is-not-available-this-prevent
LITMUS_VERIFY = False
# Litmus takes a long time to respond. Giving it a solid 10secs.
# 5secs was not enough.
LITMUS_TIMEOUT = 10

# License for Froala editor.  Can leave blank for local development
FROALA_EDITOR_LICENSE = ''
