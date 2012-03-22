from django.conf.urls.defaults   import patterns, include, url
from django.views.generic.simple import direct_to_template
from django.conf                 import settings

urlpatterns = patterns('mailer.views',
	
	url(r'^recipient/(?P<recipient_id>\d+)/preferences/?$', view='subscriptions', name='mailer-recipient-subscriptions'),
	
	url(r'^email/open/?$', view='instance_open', name='mailer-email-open'),
	url(r'^email/redirect/?$', view='redirect', name='mailer-email-redirect'),
	url(r'^email/(?P<email_id>\d+)/deactivate/?$', view='deactivate', name='mailer-email-deactivate'),
	url(r'^email/(?P<email_id>\d+)/details/?$', view='details', name='mailer-email-details'),
	url(r'^email/(?P<email_id>\d+)/map/?$', view='map_labels_fields', name='mailer-email-map'),
	url(r'^email/(?P<email_id>\d+)/update/?$', view='create_update_email', name='mailer-email-update'),
	url(r'^email/create/?$', view='create_update_email', name='mailer-email-create'),
	url(r'^$', view='list_emails', name='mailer-email-list'),
)