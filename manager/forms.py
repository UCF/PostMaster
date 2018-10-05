from django import forms
from django.forms.models import inlineformset_factory
from django.contrib.admin.widgets import FilteredSelectMultiple
from datetime import date
from datetime import timedelta

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

    def __init__(self, *args, **kwargs):
        super(EmailCreateUpdateForm, self).__init__(*args, **kwargs)
        self.fields['recipient_groups'].queryset = RecipientGroup.objects.filter(
            archived=False, preview=False)


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
    recipient_groups = forms.ModelMultipleChoiceField(queryset=RecipientGroup.objects.filter(archived=False, preview=True),
        label="Recipient groups",
        help_text='Which preview recipient group(s) this email will go to.')


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
            'archived': 'Marking this group as "Archived" will hide it in generic lists of recipient groups.',
        }


class RecipientCreateUpdateForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(RecipientCreateUpdateForm, self).__init__(*args, **kwargs)
        if self.instance.pk is not None:
            subscriptions = self.instance.subscription_category.all()
            if subscriptions:
                self.fields['unsubscribed_categories'].initial = subscriptions
            else:
                self.fields['unsubscribed_categories'].initial = SubscriptionCategory.objects.none()

            self.fields['groups'].initial = self.instance.groups.all()
        self.fields['disable'].label = 'Email Undeliverable'

    groups = forms.ModelMultipleChoiceField(queryset=RecipientGroup.objects.filter(archived=False), )
    unsubscribed_categories = forms.ModelMultipleChoiceField(
                                queryset=SubscriptionCategory.objects.all(),
                                required=False)

    def save(self, *args, **kwargs):
        # Get the categories we want the user to be subscribed to
        if self.cleaned_data.get('unsubscribed_categories') is not None:
            subscription_categories = set(self.cleaned_data.get('unsubscribed_categories'))
        else:
            subscription_categories = set()

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
        self.fields['subscription_categories'].queryset = SubscriptionCategory.objects.all()

    subscription_categories = forms.ModelMultipleChoiceField(queryset=SubscriptionCategory.objects.all(),
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

class ReportDetailForm(forms.Form):
    email_select = forms.ModelMultipleChoiceField(label="Email(s)",
        queryset=Email.objects.all(),
        help_text='Select the emails which data will be aggregegated from.',
        to_field_name='pk')

    start_date = forms.DateField(label="Start Date",
        help_text='The start date to pull data from.',
        required=True,
        initial=date.today() - timedelta(days=90))

    end_date = forms.DateField(label="End Date",
        help_text='The end date to pull data from.',
        required=True,
        initial=date.today().strftime("%m/%d/%Y"))

    days_of_week = (
        (None, " --- Select Day of Week --- "),
        (1, "Sunday"),
        (2, "Monday"),
        (3, "Tuesday"),
        (4, "Wednesday"),
        (5, "Thursday"),
        (6, "Friday"),
        (7, "Saturday")
    )

    day_of_week = forms.ChoiceField(label="Day of Week",
        choices=days_of_week,
        help_text='The day of week the emails were sent',
        required=False)

    url_filter = forms.CharField(label="URL Filter",
        help_text='Include only urls with this text in it',
        required=False)

    email_domain = forms.CharField(label="Email Domain",
        help_text='Include click from recipients email addresses than end in this string',
        required=False)

    def clean(self):
        cleaned_data = super(ReportDetailForm, self).clean()
        if cleaned_data['day_of_week'] == '':
            cleaned_data['day_of_week'] = None
        else:
            cleaned_data['day_of_week'] = int(cleaned_data['day_of_week'])

        if cleaned_data['url_filter'] == '':
            cleaned_data['url_filter'] = None

        if cleaned_data['email_domain'] == '':
            cleaned_data['email_domain'] = None

        return cleaned_data

class SettingCreateUpdateForm(forms.ModelForm):

    class Meta:
        fields = '__all__'
        model = Setting
