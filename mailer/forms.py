from django        import forms
from mailer.models import Email

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

	def clean(self):
		cleaned_data = self.cleaned_data
		html         = cleaned_data.get('html')
		source_uri   = cleaned_data.get('source_uri')

		if html == '' and source_uri == '':
			raise forms.ValidationError('Both the HTML and Source URI fields cannot be blank')

		return cleaned_data

	class Meta:
		model = Email