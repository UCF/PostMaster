from django.views.generic.simple    import direct_to_template
from mailer.models                  import Email, EmailLabelRecipientFieldMapping, URL, URLClick, InstanceOpen
from mailer.forms                   import CreateEmailForm, LabelMappingForm
from django.http                    import HttpResponseNotFound, HttpResponseForbidden,HttpResponseRedirect, HttpResponse
from django.contrib                 import messages
from django.core.urlresolvers       import reverse
from util                           import calc_url_mac
from django.conf                    import settings
from datetime                       import datetime
import urllib
import re

def list_emails(request):
	ctx  = {'emails':Email.objects.none()} 
	tmpl = 'email/list.html'

	ctx['emails'] = Email.objects.all()

	return direct_to_template(request, tmpl, ctx)

def details(request, email_id):
	ctx  = {'email':None} 
	tmpl = 'email/details.html'

	try:
		ctx['email'] = Email.objects.get(id=email_id)
	except Email.DoesNotExist:
		return HttpResponseNotFound('Email specified does not exist.')
	return direct_to_template(request, tmpl, ctx)

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
		ctx['form'] = CreateEmailForm(request.POST, **form_kwargs)
		if ctx['form'].is_valid():
			ctx['form'].save()
			if ctx['mode'] =='create':
				messages.success(request, 'Email successfully created.')
			elif ctx['mode'] == 'update':
				messages.success(request, 'Email successfully updated.')
			return HttpResponseRedirect(reverse('mailer-email-list'))
	else:
		ctx['form'] = CreateEmailForm(**form_kwargs)

	return direct_to_template(request, tmpl, ctx)

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

def redirect(request):
	'''
		Redirects based on URL and records URL click
	'''
	instance_id   = request.GET.GET('instance',  None)
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
					pass
				else:
					if mac == calc_url_mac(url_string, position, recipient_id, instance_id):
						try:
							url       = URL.objects.get(name=url_string)
							recipient = Recipient.objects.get(id=recipient_id)
							instance  = Instance.objects.get(id=instance_id)
						except URL.DoesNotExist:
							# This should have been created
							# in the mailer-process command
							# when this email was sent
							pass
						except Recipient.DoesNotExist:
							# strange
							pass
						except Instance.DoesNotExist:
							# also strange
							pass
						else:
							url_click = URLClick(recipient=recipient, url=url, position=position)
							url_click.save()
		except Exception, e:
			pass
		return HttpResponseRedirect(url_string)

def instance_open(request):
	'''
		Records an email open
	'''
	instance_id   = request.GET.get('instance',  None)
	recipient_id  = request.GET.get('recipient', None)
	mac           = request.GET.get('mac',       None)

	if timestamp and recipient_id and mac and instance_id is not None:
		try:
			instance_id  = int(instance_id)
			recipient_id = int(recipient_id)
		except ValueError:
			# corrupted
			pass
		else:
			if mac == calc_open_mac(timestamp, recipient_id, instance_id):
				try:
					recipient = Recipient.objects.get(id=recipient_id)
					instance  = Instance.objects.get(id=instance_id)
					InstanceOpen.objects.get(recipient=recipient, instance=instance)
				except Recipient.DoesNotExist:
					# strange
					pass
				except Instance.DoesNotExist:
					# also strange
					pass
				except Open.DoesNotExist:
					instance_open = InstanceOpen(recipient=recipient, instance=instance)
					instance_open.save()
	return HttpResponse(settings.DOT, content_type='image/png')