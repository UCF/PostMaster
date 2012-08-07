from django        import forms
from manager.models import Email

class EmailCreateForm(forms.ModelForm):
	
	class Meta:
		model   = Email
		exclude = ('unsubscriptions', )
