from django.conf.urls.defaults   import patterns, include, url
from django.http                 import HttpResponse
from django.views.generic.simple import direct_to_template
from django.conf                 import settings

urlpatterns = patterns('',
	url(r'', include('manager.urls')),
	url(r'^login/$', view='django.contrib.auth.views.login', kwargs={'template_name': 'login.html'}, name='login'),
	url(r'^logout/$', view='django.contrib.auth.views.logout', kwargs={'template_name': 'logout.html'}, name='logout'),
    url(r'^robots.txt', lambda x: HttpResponse('User-Agent: *\nDisallow: /', content_type='text/plain'), name='robots_file'),
)

handler403 = lambda r: direct_to_template(r, template='403.html')
handler404 = lambda r: direct_to_template(r, template='404.html')
handler500 = lambda r: direct_to_template(r, template='500.html')

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
