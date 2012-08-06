from django.conf.urls.defaults   import patterns, include, url
from mailer.views                import EmailListView, EmailCreateView, EmailSendTimeCreateView

urlpatterns = patterns('mailer.views',

	url(r'email/(?P<pk>\d+)/times/create/$', EmailSendTimeCreateView.as_view(), name='mailer-email-times-create'),
	url(r'^email/create/$',                  EmailCreateView.as_view(),         name='mailer-email-create'),

	url(r'^$', EmailListView.as_view(), name='mailer-home'),
)
