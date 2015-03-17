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

class EmailInstantSendForm(forms.Form):
    subject = forms.CharField(label="Subject", 
        help_text="Subject of the email")
    source_html_uri = forms.URLField(label="Source html uri", 
        help_text="Source URI of the email HTML")
    from_email_address = forms.EmailField(label="From email address", 
        help_text="Email address from where the sent emails will originate")
    from_friendly_name = forms.CharField(label="From friendly name", 
        help_text="A display name associated with the from email address")
    replace_delimiter = forms.CharField(label="Replace delimiter", 
        help_text="Character(s) that replacement labels are wrapped in")
    recipient_groups = forms.ModelMultipleChoiceField(queryset=RecipientGroup.objects.all(), 
        label="Recipient groups", 
        help_text='Which group(s) of recipients this email will go to. Hold down "Control", or "Command" on a Mac, to select more than one.')

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
    email_address = forms.CharField(widget=forms.TextInput(attrs={'class': 'input-medium search-query'}))


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
