from django.conf.urls.defaults   import patterns, include, url
from manager.views               import EmailListView, EmailCreateView

urlpatterns = patterns('manager.views',

	url(r'^email/create/$',                  EmailCreateView.as_view(),         name='manager-email-create'),

	url(r'^$', EmailListView.as_view(), name='manager-home'),
)
