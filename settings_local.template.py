DEBUG  = True
ADMINS = (
	#('Your Name', 'your_email@domain.com'),
)

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/static/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Base URL of the project. Needed in places where build_absolute_uri
# can't be used because there is no request object (e.g. management commands)	
# No trailing slash
PROJECT_URL = 'http://127.0.0.1:8000'

LOGIN_URL  = '/'.join([PROJECT_URL, 'login'])
LOGOUT_URL = '/'.join([PROJECT_URL, 'logout'])

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
	}
}

AMAZON_SMTP = {
	'host'    : 'email-smtp.us-east-1.amazonaws.com',
	'port'    : 465,
	'username': '',
	'password': '',
	'quota'   : 10000, # per 24 hours
	'rate'    : 1/5 # 5 per second
}

# NET Domain LDAP CONFIG
LDAP_NET_HOST        = 'ldaps://net.ucf.edu'
LDAP_NET_BASE_DN     = 'ou=People,dc=net,dc=ucf,dc=edu'
LDAP_NET_USER_SUFFIX = '@net.ucf.edu'
LDAP_NET_ATTR_MAP    = { # LDAP Object -> User Object
	'givenName' : 'first_name',
	'sn'        : 'sn',
	'mail'      : 'email'
}
LDAP_NET_SEARCH_USER = ''
LDAP_NET_SEARCH_PASS = ''

# NID of users who are allowed to manage Postmaster
MANAGERS = ()

# Set to TRUE when operating over SSL
SESSION_COOKIE_SECURE = True