from django.conf.urls.defaults   import patterns, include, url
from django.views.generic.simple import direct_to_template
from django.conf                 import settings

urlpatterns = patterns('mailer.views',
	url(r'^$', view='list_emails', name='mailer-list-emails'),
	url(r'^email/(?P<email_id>\d+)/update/?$', view='create_update_email', name='mailer-email-update'),
	url(r'^email/create/?$', view='create_update_email', name='mailer-email-create'),

)