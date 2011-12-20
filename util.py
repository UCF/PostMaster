from django.conf import settings
try:
	import requests
except ImportError:
	print 'This script utilizes the `requests` package.'
	print 'Download and install it from http://pypi.python.org/pypi/requests'
