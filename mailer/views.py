from django.views.generic.base import TemplateView
from django.views.generic.edit import CreateView
from django.views.generic.list import ListView
from django.core.urlresolvers  import reverse
from django.shortcuts          import get_object_or_404
from mailer.models             import Email
from mailer.forms              import EmailCreateForm

class EmailListView(ListView):
	model         = Email
	template_name = 'mailer/email-list.html'

class EmailCreateView(CreateView):
	model         = Email
	template_name = 'mailer/email-create.html'
	form_class    = EmailCreateForm

	def get_success_url(self):
		return reverse('mailer-home', args=(), kwargs={})
