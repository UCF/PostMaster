from django.conf.urls.defaults      import patterns, include, url
from manager.views                  import *
from django.views.generic.simple    import direct_to_template
from django.contrib.auth.decorators import login_required

urlpatterns = patterns('manager.views',

	# Emails
	url(r'^email/unsubscribe/?$',                view='unsubscribe',                                     name='manager-email-unsubscribe'),
	url(r'^email/open/?$',                       view='instance_open',                                   name='manager-email-open'),
	url(r'^email/redirect/?$',                   view='redirect',                                        name='manager-email-redirect'),
	url(r'^email/create/$',                      login_required(EmailCreateView.as_view()),              name='manager-email-create'),
	url(r'^email/(?P<pk>\d+)/delete/$',          login_required(EmailDeleteView.as_view()),              name='manager-email-delete'),
	url(r'^email/(?P<pk>\d+)/update/$',          login_required(EmailUpdateView.as_view()),              name='manager-email-update'),
	url(r'^email/(?P<pk>\d+)/instances/$',       login_required(InstanceListView.as_view()),             name='manager-email-instances'),
	url(r'^email/(?P<pk>\d+)/unsubscriptions/$', login_required(EmailUnsubscriptionsListView.as_view()), name='manager-email-unsubscriptions'),
	url(r'^email/instance/(?P<pk>\d+)/$',        login_required(InstanceDetailView.as_view()),           name='manager-email-instance'),
	url(r'^emails/$',                            login_required(EmailListView.as_view()),                name='manager-emails'),

	# Recipients
	url(r'^recipientgroups/$',                       login_required(RecipientGroupListView.as_view()),   name='manager-recipientgroups'),
	url(r'^recipientgroup/create/$',                 login_required(RecipientGroupCreateView.as_view()), name='manager-recipientgroup-create'),
	url(r'^recipientgroup/(?P<pk>\d+)/update/$',     login_required(RecipientGroupUpdateView.as_view()), name='manager-recipientgroup-update'),
	url(r'^recipientgroup/(?P<pk>\d+)/recipients/$', login_required(RecipientListView.as_view()),        name='manager-recipientgroup-recipients'),
	url(r'^recipient/(?P<pk>\d+)/$',                 login_required(RecipientDetailView.as_view()),      name='manager-recipient'),

	url(r'^$', login_required(direct_to_template), kwargs={'template':'manager/instructions.html'}, name='manager-home'),
)
