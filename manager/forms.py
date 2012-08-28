from django         import forms
from manager.models import Email, RecipientGroup, Recipient, RecipientAttribute

class EmailCreateUpdateForm(forms.ModelForm):

	class Meta:
		model   = Email
		exclude = ('unsubscriptions', )

class RecipientGroupCreateUpdateForm(forms.ModelForm):

	class Meta:
		model   = RecipientGroup
		exclude = ('recipients',)

class RecipientCreateUpdateForm(forms.ModelForm):

	def __init__(self, *args, **kwargs):
		super(RecipientCreateUpdateForm, self).__init__(*args, **kwargs)
		if self.instance.pk is not None:
			self.fields['groups'].initial = self.instance.groups.all()

	groups = forms.ModelMultipleChoiceField(queryset=RecipientGroup.objects.all(), )

	class Meta:
		model   = Recipient
		exclude = ('recipients',)

class RecipientAttributeCreateUpdateForm(forms.ModelForm):

	class Meta:
		model   = RecipientAttribute
		exclude = ('recipient',)