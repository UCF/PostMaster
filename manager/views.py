from django.views.generic.base import TemplateView
from django.views.generic.edit import CreateView
from django.views.generic.list import ListView
from django.core.urlresolvers  import reverse
from django.shortcuts          import get_object_or_404
from manager.models            import Email, RecipientGroup
from manager.forms             import EmailCreateForm, RecipientGroupCreateForm
from django.contrib            import messages

class EmailListView(ListView):
	model         = Email
	template_name = 'manager/email-list.html'

class RecipientGroupListView(ListView):
	model         = RecipientGroup
	template_name = 'manager/recipientgroup-list.html'


class EmailCreateView(CreateView):
	model         = Email
	template_name = 'manager/email-create.html'
	form_class    = EmailCreateForm

	def get_success_url(self):
		return reverse('manager-emails')

class RecipientGroupCreateView(CreateView):
	model         = RecipientGroup
	template_name = 'manager/recipientgroup-create.html'
	form_class    = RecipientGroupCreateForm

	def form_valid(self, form):
		messages.success(self.request, 'Recipient group sucessefully created.')
		return super(RecipientGroupCreateView, self).form_valid(form)

	def get_success_url(self):
		return reverse('manager-recipientgroups')