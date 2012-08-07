from django.views.generic.base   import TemplateView
from django.views.generic.edit   import CreateView, UpdateView
from django.views.generic.list   import ListView
from django.views.generic.detail import DetailView
from django.core.urlresolvers    import reverse
from django.shortcuts            import get_object_or_404
from manager.models              import Email, RecipientGroup
from manager.forms               import EmailCreateUpdateForm, RecipientGroupCreateForm
from django.contrib              import messages

#
# Emails
# 
class EmailListView(ListView):
	model               = Email
	template_name       = 'manager/email-list.html'
	context_object_name = 'emails'
	paginate_by         = 20

class EmailCreateView(CreateView):
	model         = Email
	template_name = 'manager/email-create.html'
	form_class    = EmailCreateUpdateForm

	def form_valid(self, form):
		messages.success(self.request, 'Email sucessefully created.')
		return super(EmailCreateView, self).form_valid(form)

	def get_success_url(self):
		return reverse('manager-emails')

class EmailUpdateView(UpdateView):
	model         = Email
	template_name = 'manager/email-update.html'
	form_class    = EmailCreateUpdateForm

	def form_valid(self, form):
		messages.success(self.request, 'Email sucessefully updated.')
		return super(EmailUpdateView, self).form_valid(form)

	def get_success_url(self):
		return reverse('manager-emails')
#
# Recipients
#
class RecipientGroupListView(ListView):
	model               = RecipientGroup
	template_name       = 'manager/recipientgroup-list.html'
	context_object_name = 'groups'
	paginate_by         = 20

class RecipientGroupCreateView(CreateView):
	model         = RecipientGroup
	template_name = 'manager/recipientgroup-create.html'
	form_class    = RecipientGroupCreateForm

	def form_valid(self, form):
		messages.success(self.request, 'Recipient group sucessefully created.')
		return super(RecipientGroupCreateView, self).form_valid(form)

	def get_success_url(self):
		return reverse('manager-recipientgroups')