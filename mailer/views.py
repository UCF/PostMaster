from django.views.generic.base import TemplateView
from django.views.generic.edit import CreateView
from django.views.generic.list import ListView
from django.core.urlresolvers  import reverse
from django.shortcuts          import get_object_or_404
from mailer.models             import Email, EmailSendTime
from mailer.forms              import EmailCreateForm

class EmailListView(ListView):
	model         = Email
	template_name = 'mailer/email-list.html'

class EmailCreateView(CreateView):
	model         = Email
	template_name = 'mailer/email-create.html'
	form_class    = EmailCreateForm

	def get_success_url(self):
		return reverse('mailer-email-times-create', args=(), kwargs={'pk':self.object.pk})

class EmailSendTimeCreateView(CreateView):
	model         = EmailSendTime
	template_name = 'email/emailsendtime-create.html'
	form_class    = EmailSendTimeCreateForm

	def dispatch(self, request, *args, **kwargs):
		self._email = get_object_or_404(Email, pk=kwargs['pk'])
		return super(EmailSendTimeCreateView, self).dispatch(request, *args, **kwargs)

	def get_context_data(self, **kwargs):
		context          = super(EmailSendTimeCreateView, self).get_context_data(**kwargs)
		context['email'] = self._email
		return context
