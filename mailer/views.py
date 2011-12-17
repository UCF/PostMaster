from django.views.generic.simple    import direct_to_template
from mailer.models                  import Email, EmailLabelRecipientFieldMapping
from mailer.forms                   import CreateEmailForm, LabelMappingForm
from django.http                    import HttpResponseNotFound, HttpResponseForbidden,HttpResponseRedirect
from django.contrib                 import messages
from django.core.urlresolvers       import reverse
import urllib
import re

def list_emails(request):
	ctx  = {'emails':Email.objects.none()} 
	tmpl = 'email/list.html'

	ctx['emails'] = Email.objects.all()

	return direct_to_template(request, tmpl, ctx)

def create_update_email(request, email_id=None):
	ctx  = {'form':None} 
	tmpl = 'email/create.html'

	form_kwargs = {}
	if email_id is not None:
		try:
			email = Email.objects.get(id=email_id)
		except Email.DoesNotExist:
			return HttpResponseNotFound('Email specified does not exist.')
		else:
			form_kwargs['instance'] = email

	if request.method == 'POST':
		ctx['form'] = CreateEmailForm(request.POST, **form_kwargs)
		if ctx['form'].is_valid():
			ctx['form'].save()
			messages.success(request, 'Email successfully created.')
			return HttpResponseRedirect(reverse('mailer-email-list'))
	else:
		ctx['form'] = CreateEmailForm(**form_kwargs)

	return direct_to_template(request, tmpl, ctx)

def map_email(request, email_id):
	'''
		Maps email labels to recipient fields
	'''
	ctx  = {'forms':[]}
	tmpl = 'email/map.html'

	try:
		email = Email.objects.get(id=email_id)
	except Email.DoesNotExist:
		raise HttpResponseNotFound('Email specifiec does not exist.')
	else:
		
		# Fetch remote template if needed
		html = ''
		if email.source_uri != '':
			page = urllib.urlopen(email.source_uri)
			html = page.read()
		else:
			html = email.html
		
		# Extract label names
		delimiter    = email.replacement_delimiter
		labels_names = frozenset(re.findall(delmiter + '([^' + delimiter + '])+' + delimiter, html))

		if request.method == 'POST':

		else:
			for label_name in label_names:
				try:
					label = EmailLabelRecipientFieldMapping.objects.filter(email=email, email_label=label_name)
				except EmailLabelRecipientFieldMapping.DoesNotExist:
					label = EmailLabelRecipientFieldMapping(email=email, email_label=label_name)
					label.save()
				finally:
					ctx['forms'].append(LabelMappingForm(instance=label, prefix=label_name+'_'))
		return direct_to_template(request, tmpl, ctx)