from django.views.generic.base   import TemplateView
from django.views.generic.edit   import CreateView, UpdateView
from django.views.generic.list   import ListView
from django.views.generic.detail import DetailView
from django.core.urlresolvers    import reverse
from django.shortcuts            import get_object_or_404
from manager.models              import Email, RecipientGroup, Instance, Recipient
from manager.forms               import EmailCreateUpdateForm, RecipientGroupCreateForm
from django.contrib              import messages

#
# Emails
# 
class EmailListView(ListView):
	model               = Email
	template_name       = 'manager/emails.html'
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
# Instance
#
class InstanceListView(ListView):
	model               = Instance
	template_name       = 'manager/email-instances.html'
	paginate_by         = 20
	context_object_name = 'instances'

	def dispatch(self, request, *args, **kwargs):
		self._email = get_object_or_404(Email, pk=kwargs['pk'])
		return super(InstanceListView, self).dispatch(request, *args, **kwargs)

	def get_query_set(self):
		return Instance.objects.filter(email=self._email)

	def get_context_data(self, **kwargs):
		context          = super(InstanceListView, self).get_context_data(**kwargs)
		context['email'] = self._email
		return context

#
# Recipients
#
class RecipientGroupListView(ListView):
	model               = RecipientGroup
	template_name       = 'manager/recipientgroups.html'
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

class RecipientListView(ListView):
	model               = Recipient
	template_name       = 'manager/recipientgroup-recipients.html'
	context_object_name = 'recipients'
	paginate_by         = 20

	def dispatch(self, request, *args, **kwargs):
		self._recipient_group = get_object_or_404(RecipientGroup, pk=kwargs['pk'])
		return super(RecipientListView, self).dispatch(request, *args, **kwargs)

	def get_queryset(self):
		return Recipient.objects.filter(groups=self._recipient_group)

	def get_context_data(self, **kwargs):
		context                    = super(RecipientListView, self).get_context_data(**kwargs)
		context['recipient_group'] = self._recipient_group
		return context

class RecipientDetailView(DetailView):
	model               = Recipient
	template_name       = 'manager/recipient.html'
	context_object_name = 'recipient'
