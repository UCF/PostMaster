from django.conf.urls.defaults   import patterns, include, url
from django.views.generic.simple import direct_to_template
from django.conf                 import settings

urlpatterns = patterns('',
	url(r'', include('mailer.urls')),
	url(r'^login/$', view='django.contrib.auth.views.login', kwargs={'template_name': 'login.html'}, name='login'),
	url(r'^logout/$', view='django.contrib.auth.views.logout', kwargs={'template_name': 'logout.html'}, name='logout'),
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
