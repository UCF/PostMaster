from django.views.generic.simple    import direct_to_template
from mailer.models                  import Email, EmailLabelRecipientFieldMapping, URL, URLClick, InstanceOpen, Recipient, Instance, EmailSendTime
from mailer.forms                   import CreateEmailForm, LabelMappingForm, EmailSendTimeForm
from django.http                    import HttpResponseNotFound, HttpResponseForbidden,HttpResponseRedirect, HttpResponse
from django.contrib                 import messages
from django.core.urlresolvers       import reverse
from util                           import calc_url_mac, calc_open_mac, calc_unsubscribe_mac
from django.conf                    import settings
from datetime                       import datetime
from django.contrib.auth.decorators import login_required
from django.forms.models            import inlineformset_factory
import urllib
import re
import logging

log = logging.getLogger(__name__)

EmailSendTimeFormset = inlineformset_factory(Email, EmailSendTime, form=EmailSendTimeForm, extra = 1, can_delete=True)

@login_required
def list_emails(request):
	ctx  = {'emails':Email.objects.none()} 
	tmpl = 'email/list.html'

	ctx['emails'] = Email.objects.all()

	return direct_to_template(request, tmpl, ctx)

@login_required
def details(request, email_id):
	ctx  = {'email':None} 
	tmpl = 'email/details.html'

	try:
		ctx['email'] = Email.objects.get(id=email_id)
	except Email.DoesNotExist:
		return HttpResponseNotFound('Email specified does not exist.')
	return direct_to_template(request, tmpl, ctx)

@login_required
def create_update_email(request, email_id=None):
	ctx  = {'form':None, 'mode':'create'} 
	tmpl = 'email/create_update.html'

	form_kwargs = {}
	if email_id is not None:
		try:
			email = Email.objects.get(id=email_id)
		except Email.DoesNotExist:
			return HttpResponseNotFound('Email specified does not exist.')
		else:
			form_kwargs['instance'] = email
			ctx['mode'] = 'update'

	if request.method == 'POST':
		ctx['form']  = CreateEmailForm(request.POST, **form_kwargs)
		ctx['times'] = EmailSendTimeFormset(request.POST, **dict({'prefix':'times'}, **form_kwargs))
		if ctx['form'].is_valid():
			email = ctx['form'].save()
		 	if ctx['times'].is_valid():
				times = ctx['times'].save()
				if ctx['mode'] =='create':
					messages.success(request, 'Email successfully created.')
				elif ctx['mode'] == 'update':
					messages.success(request, 'Email successfully updated.')
			return HttpResponseRedirect(reverse('mailer-email-update', kwargs={'email_id':email.id}))
	else:
		ctx['form']  = CreateEmailForm(**form_kwargs)
		ctx['times'] = EmailSendTimeFormset(**dict({'prefix':'times'}, **form_kwargs))

	return direct_to_template(request, tmpl, ctx)

@login_required
def map_labels_fields(request, email_id):
	'''
		Maps email labels to recipient fields
	'''
	ctx  = {'forms':[], 'email':None}
	tmpl = 'email/map.html'

	try:
		ctx['email'] = Email.objects.get(id=email_id)
	except Email.DoesNotExist:
		raise HttpResponseNotFound('Email specifiec does not exist.')
	else:
		
		# Fetch remote template if needed
		html = ''
		if ctx['email'].source_uri != '':
			page = urllib.urlopen(ctx['email'].source_uri)
			html = page.read()
		else:
			html = ctx['email'].html
		
		# Extract label names
		delimiter    = ctx['email'].replace_delimiter
		label_names = frozenset(re.findall(delimiter + '([^' + delimiter + ']+)' + delimiter, html))
		
		if request.method == 'POST':
			for label_name in label_names:
				try:
					label = EmailLabelRecipientFieldMapping.objects.get(email=ctx['email'], email_label=label_name)
					form = LabelMappingForm(request.POST, instance=label, prefix=label_name+'_')
					form.save()
					ctx['forms'].append(form)
				except EmailLabelRecipientFieldMapping.DoesNotExist:
					label = EmailLabelRecipientFieldMapping(email=ctx['email'], email_label=label_name)
					label.save()
			messages.success(request, 'Mappings successfully saved.')
			return HttpResponseRedirect(reverse('mailer-email-list'))
		else:
			for label_name in label_names:
				try:
					label = EmailLabelRecipientFieldMapping.objects.get(email=ctx['email'], email_label=label_name)
				except EmailLabelRecipientFieldMapping.DoesNotExist:
					label = EmailLabelRecipientFieldMapping(email=ctx['email'], email_label=label_name)
					label.save()
				finally:
					ctx['forms'].append(LabelMappingForm(instance=label, prefix=label_name+'_'))
		return direct_to_template(request, tmpl, ctx)

@login_required
def deactivate(request, email_id):
	'''
		Deactivates a specified email
	'''
	try:
		email = Email.objects.get(id=email_id)
	except Email.DoesNotExist:
		return HttpResponeNotFound('Email specified does not exist.')
	else:
		email.active = False
		email.save()
		messages.success(request, 'Email successfully deactivated.')
		return HttpResponseRedirect(reverse('mailer-email-update', kwargs={'email_id':email.id}))

@login_required
def activate(request, email_id):
	'''
		Activate a specific email
	'''
	try:
		email = Email.objects.get(id=email_id)
	except Email.DoesNotExist:
		return HttpResponeNotFound('Email specified does not exist.')
	else:
		email.active = True
		email.save()
		messages.success(request, 'Email successfully activated.')
		return HttpResponseRedirect(reverse('mailer-email-update', kwargs={'email_id':email.id}))


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
		return direct_to_template(request, 'email/unsubscribe/parameters.html')
	else:
		try:
			recipient_id = int(recipient_id)
			email_id     = int(email_id)
		except ValueError:
			# corrupted
			return direct_to_template(request, 'email/unsubscribe/parameters.html')
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
					return direct_to_template(request, 'email/unsubscribe/already.html', ctx)
				else:
					ctx['email'].unsubscriptions.add(ctx['recipient'])
					return direct_to_template(request, 'email/unsubscribe/success.html', ctx)
