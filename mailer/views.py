from django.views.generic.base import TemplateView

class Dashboard(TemplateView):
	template_name = 'base.html'