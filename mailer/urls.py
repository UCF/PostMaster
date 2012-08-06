from django.conf.urls.defaults   import patterns, include, url
from mailer.views                import Dashboard

urlpatterns = patterns('mailer.views',
	url(r'^$', Dashboard.as_view(), name='mailer-dashboard'),
)
