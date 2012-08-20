from django         import forms
from manager.models import Email, RecipientGroup

class EmailCreateUpdateForm(forms.ModelForm):

	class Meta:
		model   = Email
		exclude = ('unsubscriptions', )

class RecipientGroupCreateUpdateForm(forms.ModelForm):

	class Meta:
		model   = RecipientGroup
		exclude = ('recipients',)