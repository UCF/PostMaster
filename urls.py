from django.conf.urls.defaults   import patterns, include, url
from django.views.generic.simple import direct_to_template
from django.conf                 import settings

urlpatterns = patterns('',
	url(r'', include('mailer.urls')),
	url(r'^login/$', view='django.contrib.auth.views.login', kwargs={'template_name': 'login.html'}, name='login'),
	url(r'^logout/$', view='django.contrib.auth.views.logout', kwargs={'template_name': 'logout.html'}, name='logout'),
	url(r'^password_change/$', view='django.contrib.auth.views.password_change', kwargs={'template_name': 'password_change.html'}, name='password-change'),
	url(r'^password_change_done/$', view='django.contrib.auth.views.password_change_done', kwargs={'template_name': 'password_change_done.html'}, name='password-change-done'),
)

handler500 = lambda r: direct_to_template(r, template='500.html')
handler404 = lambda r: direct_to_template(r, template='404.html')

if settings.DEBUG:
	urlpatterns += patterns('',
		(r'^%s(?P<path>.*)$' % settings.MEDIA_URL[1:],
			'django.views.static.serve',
			{
				'document_root': settings.MEDIA_ROOT,
				'show_indexes' : True,
			}
		),
	)
