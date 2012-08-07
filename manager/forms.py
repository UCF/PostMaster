from django         import forms
from manager.models import Email, RecipientGroup

class EmailCreateForm(forms.ModelForm):

	class Meta:
		model   = Email
		exclude = ('unsubscriptions', )

class RecipientGroupCreateForm(forms.ModelForm):

	class Meta:
		model   = RecipientGroup
		exclude = ('recipients',)