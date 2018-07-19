from django import forms
from django.forms.models import inlineformset_factory
from django.contrib.admin.widgets import FilteredSelectMultiple

from manager.models import Email
from manager.models import PreviewInstance
from manager.models import Recipient
from manager.models import RecipientAttribute
from manager.models import RecipientGroup
from manager.models import Setting
from manager.models import SubscriptionCategory


class EmailSearchForm(forms.Form):
    search_query = forms.CharField(widget=forms.TextInput())

class EmailCreateUpdateForm(forms.ModelForm):

    class Meta:
        model = Email
        exclude = ('unsubscriptions', 'preview_est_time', 'live_est_time', 'send_override', 'creator',)


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
        help_text="Character(s) that replacement labels are wrapped in",
        initial="!@!")
    recipient_groups = forms.ModelMultipleChoiceField(queryset=RecipientGroup.objects.filter(archived=False),
        label="Recipient groups",
        help_text='Which group(s) of recipients this email will go to. Hold down "Control", or "Command" on a Mac, to select more than one.')


class PreviewInstanceLockForm(forms.ModelForm):
    """
    Form for locking the preview instance content
    """

    class Meta:
        model = PreviewInstance
        fields = ('lock_content', )


class RecipientGroupSearchForm(forms.Form):
    search_query = forms.CharField(widget=forms.TextInput())


class RecipientGroupCreateForm(forms.ModelForm):

    class Meta:
        model = RecipientGroup
        exclude = ('recipients', 'archived')


class RecipientGroupUpdateForm(forms.ModelForm):

    class Meta:
        model = RecipientGroup
        exclude = ('recipients',)
        labels = {
            'archived': 'Archive Group',
        }
        help_texts = {
            'archived': 'Marking a Recipient Group as "Archived" will hide this group in generic lists of Recipient Groups.',
        }


class RecipientCreateUpdateForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(RecipientCreateUpdateForm, self).__init__(*args, **kwargs)
        if self.instance.pk is not None:
            self.fields['subscription_categories'].initial = self.instance.subscription_category.all()
            self.fields['groups'].initial = self.instance.groups.all()
        self.fields['disable'].label = 'Email Undeliverable'

    groups = forms.ModelMultipleChoiceField(queryset=RecipientGroup.objects.filter(archived=False), )
    subscription_categories = forms.ModelMultipleChoiceField(
                                queryset=SubscriptionCategory.objects.all(),
                                required=False)

    def save(self, *args, **kwargs):
        # Get the categories we want the user to be subscribed to
        subscription_categories = set(self.cleaned_data.get('subscription_categories'))
        all_categories = set(SubscriptionCategory.objects.all())

        for category in subscription_categories:
            category.unsubscriptions.add(self.instance)

        # Remove everything they did not click on
        unsubscriptions = list(all_categories - subscription_categories)

        for category in unsubscriptions:
            category.unsubscriptions.remove(self.instance)
        return super(RecipientCreateUpdateForm, self).save(*args, **kwargs)

    class Meta:
        model = Recipient
        exclude = ('recipients',)


class RecipientCSVImportForm(forms.Form):
    existing_group_name = forms.ModelChoiceField(
        queryset=RecipientGroup.objects.filter(archived=False),
        required=False,
        help_text='If adding recipients to an existing recipient group, choose the group name.',
        to_field_name='name')
    new_group_name = forms.CharField(
        help_text='If creating a new recipient group, enter the name.',
        required=False)
    column_order = forms.CharField(
        help_text='Enter, seperated by commas, the name of the columns in your CSV (i.e. first_name,last_name,email,preferred_name).')
    skip_first_row = forms.BooleanField(help_text='Check if you have column names in your first row.', required=False)
    csv_file = forms.FileField()

    def clean(self):
        if any(self.errors):
            return
        else:
            cleaned_data = super(RecipientCSVImportForm, self).clean()
            existing_group_name = cleaned_data.get('existing_group_name')
            new_group_name = cleaned_data.get('new_group_name')

            if existing_group_name and new_group_name:
                raise forms.ValidationError('Please specify either a new or existing group name.')
            elif not existing_group_name and not new_group_name:
                raise forms.ValidationError('Please specify either a new or existing group name.')
            return cleaned_data


class RecipientAttributeCreateForm(forms.ModelForm):

    class Meta:
        model = RecipientAttribute
        fields = ('name', 'value')


class RecipientAttributeUpdateForm(forms.ModelForm):

    class Meta:
        model = RecipientAttribute
        exclude = ('recipient', 'name',)


RecipientAttributeFormSet = inlineformset_factory(Recipient, RecipientAttribute, form=RecipientAttributeCreateForm, extra=1, can_delete=True)


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

class SubscriptionCategoryForm(forms.ModelForm):
    class Meta:
        model = SubscriptionCategory
        fields = (
            'name',
            'description',
            'cannot_unsubscribe',
            'applies_to'
        )

class SettingCreateUpdateForm(forms.ModelForm):

    class Meta:
        fields = '__all__'
        model = Setting
