from django        import forms
from mailer.models import Email

class CreateEmailForm(forms.ModelForm):

	class Meta:
		model = Email