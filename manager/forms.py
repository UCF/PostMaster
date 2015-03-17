from django import forms

from manager.models import Email
from manager.models import Recipient
from manager.models import RecipientAttribute
from manager.models import RecipientGroup
from manager.models import Setting


class EmailCreateUpdateForm(forms.ModelForm):

    class Meta:
        model = Email
        exclude = ('unsubscriptions', 'preview_est_time', 'live_est_time', 'send_override', )


class RecipientGroupCreateUpdateForm(forms.ModelForm):

    class Meta:
        model = RecipientGroup
        exclude = ('recipients',)


class RecipientCreateUpdateForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(RecipientCreateUpdateForm, self).__init__(*args, **kwargs)
        if self.instance.pk is not None:
            self.fields['groups'].initial = self.instance.groups.all()
        self.fields['disable'].label = 'Email Undeliverable to this Address'

    groups = forms.ModelMultipleChoiceField(queryset=RecipientGroup.objects.all(), )

    class Meta:
        model = Recipient
        exclude = ('recipients',)


class RecipientAttributeCreateForm(forms.ModelForm):

    class Meta:
        model = RecipientAttribute
        exclude = ('recipient',)


class RecipientAttributeUpdateForm(forms.ModelForm):

    class Meta:
        model = RecipientAttribute
        exclude = ('recipient', 'name',)


class RecipientSearchForm(forms.Form):
    email_address = forms.CharField(widget=forms.TextInput())


class RecipientSubscriptionsForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(RecipientSubscriptionsForm, self).__init__(*args, **kwargs)
        self.fields['subscribed_emails'].queryset = self.instance.subscriptions

    subscribed_emails = forms.ModelMultipleChoiceField(queryset=Email.objects.none(),
                                                       required=False)

    class Meta:
        model = Recipient
        fields = ()


class SettingCreateUpdateForm(forms.ModelForm):

    class Meta:
        model = Setting
