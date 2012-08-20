from django.views.generic.base   import TemplateView
from django.views.generic.edit   import CreateView, UpdateView, DeleteView
from django.views.generic.list   import ListView
from django.views.generic.detail import DetailView
from django.core.urlresolvers    import reverse
from django.shortcuts            import get_object_or_404
from manager.models              import Email, RecipientGroup, Instance, Recipient, URL, URLClick, InstanceOpen
from manager.forms               import EmailCreateUpdateForm, RecipientGroupCreateUpdateForm
from django.contrib              import messages
from django.http                 import HttpResponse, HttpResponseRedirect
from util                        import calc_url_mac, calc_open_mac, calc_unsubscribe_mac
from django.conf                 import settings
from django.views.generic.simple import direct_to_template
import urllib
import logging

log = logging.getLogger(__name__)

##
# Mixins
##
class EmailsMixin(object):
	def get_context_data(self, **kwargs):
		context            = super(EmailsMixin, self).get_context_data(**kwargs)
		context['section'] = 'emails'
		return context

class RecipientsMixin(object):
	def get_context_data(self, **kwargs):
		context            = super(RecipientsMixin, self).get_context_data(**kwargs)
		context['section'] = 'recipients'
		return context

##
# Emails
##
class EmailListView(EmailsMixin, ListView):
	model               = Email
	template_name       = 'manager/emails.html'
	context_object_name = 'emails'
	paginate_by         = 20

class EmailCreateView(EmailsMixin, CreateView):
	model         = Email
	template_name = 'manager/email-create.html'
	form_class    = EmailCreateUpdateForm

	def form_valid(self, form):
		messages.success(self.request, 'Email sucessefully created.')
		return super(EmailCreateView, self).form_valid(form)

	def get_success_url(self):
		return reverse('manager-emails')

class EmailUpdateView(EmailsMixin, UpdateView):
	model         = Email
	template_name = 'manager/email-update.html'
	form_class    = EmailCreateUpdateForm

	def form_valid(self, form):
		messages.success(self.request, 'Email sucessefully updated.')
		return super(EmailUpdateView, self).form_valid(form)

	def get_success_url(self):
		return reverse('manager-emails')

class EmailDeleteView(EmailsMixin, DeleteView):
	model                = Email
	template_name        = 'manager/email-delete.html'
	template_name_suffix = '-delete-confirm'

	def get_success_url(self):
		messages.success(self.request, 'Email sucessefully deleted.')
		return reverse('manager-emails')

class EmailUnsubscriptionsListView(EmailsMixin, ListView):
	model               = Recipient
	template_name       = 'manager/email-unsubscriptions.html'
	context_object_name = 'recipients'
	paginate_by         = 20

	def dispatch(self, request, *args, **kwargs):
		self._email = get_object_or_404(Email, pk=kwargs['pk'])
		return super(EmailUnsubscriptionsListView, self).dispatch(request, *args, **kwargs)

	def get_queryset(self):
		return self._email.unsubscriptions.all()

	def get_context_data(self, **kwargs):
		context          = super(EmailUnsubscriptionsListView, self).get_context_data(**kwargs)
		context['email'] = self._email
		return context

class InstanceListView(EmailsMixin, ListView):
	model               = Instance
	template_name       = 'manager/email-instances.html'
	paginate_by         = 20
	context_object_name = 'instances'

	def dispatch(self, request, *args, **kwargs):
		self._email = get_object_or_404(Email, pk=kwargs['pk'])
		return super(InstanceListView, self).dispatch(request, *args, **kwargs)

	def get_queryset(self):
		return Instance.objects.filter(email=self._email)

	def get_context_data(self, **kwargs):
		context          = super(InstanceListView, self).get_context_data(**kwargs)
		context['email'] = self._email
		return context

class InstanceDetailView(EmailsMixin, DetailView):
	model               = Instance
	template_name       = 'manager/email-instance.html'
	context_object_name = 'instance'

##
# Recipients
##
class RecipientGroupListView(RecipientsMixin, ListView):
	model               = RecipientGroup
	template_name       = 'manager/recipientgroups.html'
	context_object_name = 'groups'
	paginate_by         = 20

class RecipientGroupCreateView(RecipientsMixin, CreateView):
	model         = RecipientGroup
	template_name = 'manager/recipientgroup-create.html'
	form_class    = RecipientGroupCreateUpdateForm

	def form_valid(self, form):
		messages.success(self.request, 'Recipient group sucessefully created.')
		return super(RecipientGroupCreateView, self).form_valid(form)

	def get_success_url(self):
		return reverse('manager-recipientgroups')

class RecipientGroupUpdateView(RecipientsMixin, UpdateView):
	model         = RecipientGroup
	template_name = 'manager/recipientgroup-update.html'
	form_class    = RecipientGroupCreateUpdateForm

	def form_valid(self, form):
		messages.success(self.request, 'Recipient group sucessefully updated.')
		return super(RecipientGroupUpdateView, self).form_valid(form)

	def get_success_url(self):
		return reverse('manager-recipientgroups')

class RecipientListView(RecipientsMixin, ListView):
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

class RecipientDetailView(RecipientsMixin, DetailView):
	model               = Recipient
	template_name       = 'manager/recipient.html'
	context_object_name = 'recipient'

##
# Tracking
##
def redirect(request):
	'''
		Redirects based on URL and records URL click
	'''
	instance_id   = request.GET.get('instance',  None)
	url_string    = request.GET.get('url',       None)
	position      = request.GET.get('position',  None)
	recipient_id  = request.GET.get('recipient', None)
	mac           = request.GET.get('mac',       None)

	if not url_string:
		pass # Where do we go?
	else:
		url_string = urllib.unquote(url_string)
		# No matter what happens, make sure the redirection works
		try:
			if position and recipient_id and mac and instance_id:
				try:
					position     = int(position)
					recipient_id = int(recipient_id)
					instance_id  = int(instance_id)
				except ValueError:
					log.error('value error')
					pass
				else:
					if mac == calc_url_mac(url_string, position, recipient_id, instance_id):
						try:
							recipient = Recipient.objects.get(id=recipient_id)
							instance  = Instance.objects.get(id=instance_id)
							url       = URL.objects.get(name=url_string, position=position, instance=instance)
						except URL.DoesNotExist:
							# This should have been created
							# in the mailer-process command
							# when this email was sent
							pass
						except Recipient.DoesNotExist:
							# strange
							log.error('bad recipient')
							pass
						except Instance.DoesNotExist:
							# also strange
							log.error('bad instance')
							pass
						else:
							url_click = URLClick(recipient=recipient, url=url)
							url_click.save()
							log.debug('url click saved')
					else:
						log.error('wrong mac')
			else:
				log.error('something none')
		except Exception, e:
			log.error(str(e))
			pass
		return HttpResponseRedirect(url_string)

def instance_open(request):
	'''
		Records an email open
	'''
	instance_id   = request.GET.get('instance',  None)
	recipient_id  = request.GET.get('recipient', None)
	mac           = request.GET.get('mac',       None)

	if recipient_id and mac and instance_id is not None:
		try:
			instance_id  = int(instance_id)
			recipient_id = int(recipient_id)
		except ValueError:
			# corrupted
			pass
		else:
			if mac == calc_open_mac(recipient_id, instance_id):
				try:
					recipient = Recipient.objects.get(id=recipient_id)
					instance  = Instance.objects.get(id=instance_id)
					InstanceOpen.objects.get(recipient=recipient, instance=instance)
				except Recipient.DoesNotExist:
					# strange
					log.error('bad recipient')
					pass
				except Instance.DoesNotExist:
					# also strange
					log.error('bad instance')
					pass
				except InstanceOpen.DoesNotExist:
					instance_open = InstanceOpen(recipient=recipient, instance=instance)
					instance_open.save()
					log.debug('open saved')
	return HttpResponse(settings.DOT, content_type='image/png')

def unsubscribe(request):
	'''
		Unsubcribe a recipient from a particular email
	'''
	ctx  = {'email':None, 'recipient':None}

	email_id     = request.GET.get('email',     None)
	recipient_id = request.GET.get('recipient', None)
	mac          = request.GET.get('mac',       None)

	if email_id is None or recipient_id is None or mac is None or mac != calc_unsubscribe_mac(recipient_id, email_id):
		return direct_to_template(request, 'manager/email-unsubscribe-parameters.html')
	else:
		try:
			recipient_id = int(recipient_id)
			email_id     = int(email_id)
		except ValueError:
			# corrupted
			return direct_to_template(request, 'manager/email-unsubscribe-parameters.html')
		else:
			try:
				ctx['recipient'] = Recipient.objects.get(id=recipient_id)
				ctx['email']     = Email.objects.get(id=email_id)
			except Recipient.DoesNotExist:
				log.error('Bad unsubscribe recipient id %d for email id %d' % (recipient_id, email_id))
			except Email.DoesNotExist:
				log.error('Bad unsubscribe email id %d for recipient id %d' % (recipient_id, email_id))
			else:
				if ctx['recipient'] in ctx['email'].unsubscriptions.all():
					log.info('Recipeint %d already unsubscribed from email %d' % (recipient_id, email_id))
					return direct_to_template(request, 'manager/email-unsubscribe-already.html', ctx)
				else:
					ctx['email'].unsubscriptions.add(ctx['recipient'])
					return direct_to_template(request, 'manager/email-unsubscribe.html', ctx)