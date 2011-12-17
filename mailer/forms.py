from django                      import forms
from django.forms.extras.widgets import SelectDateWidget
from mailer.models               import Email, EmailLabelRecipientFieldMapping, Recipient

class CreateEmailForm(forms.ModelForm):
	def __init__(self, *args, **kwargs):
		super(CreateEmailForm, self).__init__(*args, **kwargs)
		
		# Preserve help text of redefined fields since it is not inherited
		for name, form_field in self.fields.items():
			for model_field in Email._meta.fields:
				if name == model_field.name:
					self.fields[name].help_text = model_field.help_text

	html       = forms.CharField(label='HTML', widget=forms.Textarea())
	source_uri = forms.CharField(label='Source URI')
	start_date = forms.DateField(widget=SelectDateWidget())
	send_time  = forms.CharField(label='Send time (24 Hour)')

	def clean(self):
		cleaned_data = self.cleaned_data
		html         = cleaned_data.get('html')
		source_uri   = cleaned_data.get('source_uri')

		if html == '' and source_uri == '':
			raise forms.ValidationError('Both the HTML and Source URI fields cannot be blank.')
		elif html != '' and source_uri != '':
			raise forms.ValidationError('Both the HTML and Source URI fields cannot contain content.')

		return cleaned_data

	class Meta:
		model = Email

class LabelMappingForm(forms.ModelForm):

	recipient_field = forms.ChoiceField(choices=Recipient.LABELABLE_FIELD_NAMES)
	
	class Meta:
		model   = EmailLabelRecipientFieldMapping
		exclude = ('email', 'email_label')