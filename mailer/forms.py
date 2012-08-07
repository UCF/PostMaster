from django        import forms
from mailer.models import Email

class EmailCreateForm(forms.ModelForm):

	def clean(self):
		cleaned_data = super(EmailCreateForm, self).clean()
		if cleaned_data['html'] == '' and cleaned_data['source_uri'] == '':
			raise forms.ValidationError('Either the HTML and Source URI field must not be blank.')
		return cleaned_data

	class Meta:
		model   = Email
		exclude = ('unsubscriptions', )
