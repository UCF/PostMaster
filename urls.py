from django.conf.urls            import include, url
from django.http                 import HttpResponse
from django.views.generic        import TemplateView
from django.conf                 import settings
from django.conf.urls.static     import static

from django.contrib.auth.views   import LoginView, LogoutView

urlpatterns = [
	url(r'', include('manager.urls')),
	url(r'^login/$', LoginView.as_view(template_name='login.html'), name='login'),
	url(r'^logout/$', LogoutView.as_view(template_name='logout.html'), name='logout'),
	url(r'^robots.txt', lambda x: HttpResponse('User-Agent: *\nDisallow: /', content_type='text/plain'), name='robots_file'),
]

handler403 = lambda r, e: url(r, TemplateView.as_view(template_name='403.html'))
handler404 = lambda r, e: url(r, TemplateView.as_view(template_name='404.html'))
handler500 = lambda r: url(r, TemplateView.as_view(template_name='500.html'))
