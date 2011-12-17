from django.views.generic.simple    import direct_to_template
from mailer.models                  import Email
from mailer.forms                   import CreateEmailForm
from django.http                    import HttpResponseNotFound, HttpResponseForbidden,HttpResponseRedirect
from django.contrib                 import messages
from django.core.urlresolvers       import reverse

def list_emails(request):
	ctx  = {} 
	tmpl = 'email/list.html'

	ctx['emails'] = Email.objects.all()

	return direct_to_template(request, tmpl, ctx)

def create_update_email(request, email_id=None):
	ctx  = {} 
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