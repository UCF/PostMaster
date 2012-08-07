from django.conf.urls.defaults   import patterns, include, url
from mailer.views                import EmailListView, EmailCreateView

urlpatterns = patterns('mailer.views',

	url(r'^email/create/$',                  EmailCreateView.as_view(),         name='mailer-email-create'),

	url(r'^$', EmailListView.as_view(), name='mailer-home'),
)
