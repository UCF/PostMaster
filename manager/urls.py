from django.conf.urls.defaults   import patterns, include, url
from manager.views               import *

urlpatterns = patterns('manager.views',

	# Emails
	url(r'^emails/$',                   EmailListView.as_view(),   name='manager-emails'),
	url(r'^email/create/$',             EmailCreateView.as_view(), name='manager-email-create'),
	url(r'^email/(?P<pk>\d+)/update/$', EmailUpdateView.as_view(), name='manager-email-update'),

	# Recipients
	url(r'^recipient/groups/$',       RecipientGroupListView.as_view(),   name='manager-recipientgroups'),
	url(r'^recipient/group/create/$', RecipientGroupCreateView.as_view(), name='manager-recipientgroup-create'),

	url(r'^$', EmailListView.as_view(), name='manager-home'),
)
