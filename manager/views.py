from datetime import date
from datetime import datetime
import logging
from util import calc_open_mac
from util import calc_unsubscribe_mac
from util import calc_unsubscribe_mac_old
from util import calc_url_mac
import urllib

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.generic.base import TemplateView
from django.views.generic.edit import CreateView
from django.views.generic.edit import DeleteView
from django.views.generic.edit import FormView
from django.views.generic.list import ListView
from django.views.generic.edit import UpdateView
from django.views.generic.detail import DetailView
from django.views.generic.simple import direct_to_template
from django.forms.util import ErrorList

from manager.forms import EmailCreateUpdateForm
from manager.forms import RecipientAttributeCreateForm
from manager.forms import RecipientAttributeUpdateForm
from manager.forms import RecipientCreateUpdateForm
from manager.forms import RecipientGroupCreateUpdateForm
from manager.forms import RecipientSearchForm
from manager.forms import RecipientSubscriptionsForm
from manager.forms import SettingCreateUpdateForm
from manager.forms import RecipientCSVImportForm
from manager.models import Email
from manager.models import Instance
from manager.models import InstanceOpen
from manager.models import PreviewInstance
from manager.models import RecipientAttribute
from manager.models import Recipient
from manager.models import RecipientGroup
from manager.models import Setting
from manager.models import URL
from manager.models import URLClick
from manager.utils import CSVImport


log = logging.getLogger(__name__)


##
# Mixins
##
class EmailsMixin(object):
    def get_context_data(self, **kwargs):
        context = super(EmailsMixin, self).get_context_data(**kwargs)
        context['section'] = 'emails'
        return context


class RecipientGroupsMixin(object):
    def get_context_data(self, **kwargs):
        context = super(RecipientGroupsMixin, self).get_context_data(**kwargs)
        context['section'] = 'recipientgroups'
        return context


class RecipientsMixin(object):
    def get_context_data(self, **kwargs):
        context = super(RecipientsMixin, self).get_context_data(**kwargs)
        context['section'] = 'recipients'
        return context


class SettingsMixin(object):
    def get_context_data(self, **kwargs):
        context = super(SettingsMixin, self).get_context_data(**kwargs)
        context['section'] = 'settings'
        return context


class OverviewListView(ListView):
    template_name = 'manager/instructions.html'
    context_object_name = 'emails'

    def get_queryset(self):
        return Email.objects.sending_today().order_by('send_time')

    def get_context_data(self, **kwargs):
        context = super(OverviewListView, self).get_context_data(**kwargs)

        try:
            contact_info = Setting.objects.get(
                name='office_hours_contact_info')
            context['office_hours_contact_info'] = contact_info.value
        except Setting.DoesNotExist:
            pass

        try:
            contact_info = Setting.objects.get(
                name='after_hours_contact_info')
            context['after_hours_contact_info'] = contact_info.value
        except Setting.DoesNotExist:
            pass

        return context


##
# Emails
##
class EmailListView(EmailsMixin, ListView):
    model = Email
    template_name = 'manager/emails.html'
    context_object_name = 'emails'
    paginate_by = 20


class EmailCreateView(EmailsMixin, CreateView):
    model = Email
    template_name = 'manager/email-create.html'
    form_class = EmailCreateUpdateForm

    def form_valid(self, form):
        email = form.instance

        # Enable override send in case the service interval misses the email
        now = datetime.now()
        if email.is_sending_today(now) and email.send_time >= now.time():
            email.send_override = True
        else:
            email.send_override = False

        messages.success(self.request, 'Email successfully created.')
        return super(EmailCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('manager-email-update',
                       args=(),
                       kwargs={'pk': self.object.pk})


class EmailUpdateView(EmailsMixin, UpdateView):
    model = Email
    template_name = 'manager/email-update.html'
    form_class = EmailCreateUpdateForm

    def form_valid(self, form):
        email = form.instance

        # Enable override send in case the service interval misses the email
        now = datetime.now()
        if 'start_date' in form.changed_data or \
                'send_time' in form.changed_data or \
                'recurrence' in form.changed_data:
            if email.is_sending_today(now) and email.send_time >= now.time():
                email.send_override = True
            else:
                email.send_override = False

            # Clear the estimated times
            email.preview_est_time = None
            email.live_est_time = None

        messages.success(self.request, 'Email successfully updated.')
        return super(EmailUpdateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('manager-email-update',
                       args=(),
                       kwargs={'pk': self.object.pk})


class EmailDeleteView(EmailsMixin, DeleteView):
    model = Email
    template_name = 'manager/email-delete.html'
    template_name_suffix = '-delete-confirm'

    def get_success_url(self):
        messages.success(self.request, 'Email successfully deleted.')
        return reverse('manager-emails')


class EmailUnsubscriptionsListView(EmailsMixin, ListView):
    model = Recipient
    template_name = 'manager/email-unsubscriptions.html'
    context_object_name = 'recipients'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        self._email = get_object_or_404(Email, pk=kwargs['pk'])
        return super(EmailUnsubscriptionsListView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self._email.unsubscriptions.all()

    def get_context_data(self, **kwargs):
        context = super(EmailUnsubscriptionsListView,
                        self).get_context_data(**kwargs)
        context['email'] = self._email
        return context


class InstanceListView(EmailsMixin, ListView):
    model = Instance
    template_name = 'manager/email-instances.html'
    paginate_by = 20
    context_object_name = 'instances'

    def dispatch(self, request, *args, **kwargs):
        self._email = get_object_or_404(Email, pk=kwargs['pk'])
        return super(InstanceListView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Instance.objects.filter(email=self._email)

    def get_context_data(self, **kwargs):
        context = super(InstanceListView, self).get_context_data(**kwargs)
        context['email'] = self._email
        return context


class InstanceDetailView(EmailsMixin, DetailView):
    model = Instance
    template_name = 'manager/email-instance.html'
    context_object_name = 'instance'


##
# Recipients Groups
##
class RecipientGroupListView(RecipientGroupsMixin, ListView):
    model = RecipientGroup
    template_name = 'manager/recipientgroups.html'
    context_object_name = 'groups'
    paginate_by = 20


class RecipientGroupCreateView(RecipientGroupsMixin, CreateView):
    model = RecipientGroup
    template_name = 'manager/recipientgroup-create.html'
    form_class = RecipientGroupCreateUpdateForm

    def form_valid(self, form):
        messages.success(self.request, 'Recipient group successfully created.')
        return super(RecipientGroupCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('manager-recipientgroup-update',
                       args=(),
                       kwargs={'pk': self.object.pk})


class RecipientGroupUpdateView(RecipientGroupsMixin, UpdateView):
    model = RecipientGroup
    template_name = 'manager/recipientgroup-update.html'
    form_class = RecipientGroupCreateUpdateForm

    def form_valid(self, form):
        messages.success(self.request, 'Recipient group successfully updated.')
        return super(RecipientGroupUpdateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('manager-recipientgroup-update',
                       args=(),
                       kwargs={'pk': self.object.pk})


class RecipientGroupRecipientListView(RecipientGroupsMixin, ListView):
    model = Recipient
    template_name = 'manager/recipientgroup-recipients.html'
    context_object_name = 'recipients'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        self._recipient_group = get_object_or_404(RecipientGroup,
                                                  pk=kwargs['pk'])
        return super(RecipientGroupRecipientListView, self).dispatch(request,
                                                                     *args,
                                                                     **kwargs)

    def get_queryset(self):
        return Recipient.objects.filter(groups=self._recipient_group)

    def get_context_data(self, **kwargs):
        context = super(RecipientGroupRecipientListView,
                        self).get_context_data(**kwargs)
        context['recipientgroup'] = self._recipient_group
        return context


##
# Recipients
##
class RecipientListView(RecipientsMixin, ListView):
    model = Recipient
    template_name = 'manager/recipients.html'
    context_object_name = 'recipients'
    paginate_by = 20

    def get_queryset(self):
        self._search_form = RecipientSearchForm(self.request.GET)
        self._search_valid = self._search_form.is_valid()
        if self._search_valid:
            return Recipient.objects.filter(email_address__icontains=self._search_form.cleaned_data['email_address'])
        else:
            return Recipient.objects.all()

    def get_context_data(self, **kwargs):
        context = super(RecipientListView, self).get_context_data(**kwargs)
        context['search_form'] = self._search_form
        context['search_valid'] = self._search_valid
        return context


class RecipientCreateView(RecipientsMixin, CreateView):
    model = Recipient
    template_name = 'manager/recipient-create.html'
    context_object_name = 'recipient'
    form_class = RecipientCreateUpdateForm

    def form_valid(self, form):
        messages.success(self.request, 'Recipient successfully created.')
        response = super(RecipientCreateView, self).form_valid(form)
        self.object.set_groups(form.cleaned_data['groups'])
        return response

    def get_success_url(self):
        return reverse('manager-recipient-update',
                       args=(),
                       kwargs={'pk': self.object.pk})


class RecipientUpdateView(RecipientsMixin, UpdateView):
    model = Recipient
    template_name = 'manager/recipient-update.html'
    form_class = RecipientCreateUpdateForm

    def form_valid(self, form):
        messages.success(self.request, 'Recipient successfully updated.')
        self.object.set_groups(form.cleaned_data['groups'])
        return super(RecipientUpdateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('manager-recipient-update',
                       args=(),
                       kwargs={'pk': self.object.pk})


class RecipientAttributeListView(RecipientsMixin, ListView):
    model = RecipientAttribute
    template_name = 'manager/recipient-recipientattributes.html'
    context_object_name = 'attributes'
    pageinate_by = 20

    def dispatch(self, request, *args, **kwargs):
        self._recipient = get_object_or_404(Recipient, pk=kwargs['pk'])
        return super(RecipientAttributeListView, self).dispatch(request,
                                                                *args,
                                                                **kwargs)

    def get_queryset(self):
        return RecipientAttribute.objects.filter(recipient=self._recipient)

    def get_context_data(self, **kwargs):
        context = super(RecipientAttributeListView,
                        self).get_context_data(**kwargs)
        context['recipient'] = self._recipient
        return context


class RecipientAttributeCreateView(RecipientsMixin, CreateView):
    model = RecipientAttribute
    template_name = 'manager/recipientattribute-create.html'
    form_class = RecipientAttributeCreateForm

    def dispatch(self, request, *args, **kwargs):
        self._recipient = get_object_or_404(Recipient, pk=kwargs['pk'])
        return super(RecipientAttributeCreateView, self).dispatch(request,
                                                                  *args,
                                                                  **kwargs)

    def get_context_data(self, **kwargs):
        context = super(RecipientAttributeCreateView,
                        self).get_context_data(**kwargs)
        context['recipient'] = self._recipient
        return context

    def form_valid(self, form):
        form.instance.recipient = self._recipient

        # Check the unique_together(recipient, name) here. It can't be done in
        # the Form class
        name = form.cleaned_data['name']
        try:
            RecipientAttribute.objects.get(name=name,
                                           recipient=self._recipient)
        except RecipientAttribute.DoesNotExist:
            pass
        else:
            form._errors['name'] = ErrorList([u'A attribute with that name already exists for this recipient.'])
            return super(RecipientAttributeCreateView, self).form_invalid(form)

        return super(RecipientAttributeCreateView, self).form_valid(form)

    def get_success_url(self):
        messages.success(self.request,
                         'Recipient attribute successfully created.')
        return reverse('manager-recipient-recipientattributes',
                       args=(),
                       kwargs={'pk': self._recipient.pk})


class RecipientAttributeUpdateView(RecipientsMixin, UpdateView):
    model = RecipientAttribute
    template_name = 'manager/recipientattribute-update.html'
    form_class = RecipientAttributeUpdateForm
    context_object_name = 'attribute'

    def get_success_url(self):
        messages.success(self.request,
                         'Recipient attribute successfully updated.')
        return reverse('manager-recipientattribute-update',
                       args=(),
                       kwargs={'pk': self.object.pk})


class RecipientAttributeDeleteView(RecipientsMixin, DeleteView):
    model = RecipientAttribute
    template_name = 'manager/recipientattribute-delete.html'
    template_name_suffix = '-delete-confirm'
    context_object_name = 'attribute'

    def get_success_url(self):
        messages.success(self.request, 'Attribute successfully deleted.')
        return reverse('manager-recipient-recipientattributes',
                       args=(),
                       kwargs={'pk': self.object.recipient.pk})


class RecipientSubscriptionsUpdateView(UpdateView):
    model = Recipient
    template_name = 'manager/recipient-subscriptions.html'
    form_class = RecipientSubscriptionsForm

    def get_object(self, *args, **kwargs):
        mac = self.request.GET.get('mac', None)

        recipient_id = self.request.GET.get('recipient', None)
        email_id = self.request.GET.get('email',     None)

        # Old style unsubscribe
        if recipient_id is not None and email_id is not None:
            try:
                recipient = Recipient.objects.get(pk=recipient_id)
            except Recipient.DoesNotExist:
                raise PermissionDenied
            if mac is None or mac != calc_unsubscribe_mac_old(recipient_id, email_id):
                raise PermissionDenied
        else:
            recipient = super(RecipientSubscriptionsUpdateView, self).get_object()
            # Validate MAC
            if mac is None or mac != calc_unsubscribe_mac(recipient.pk):
                raise PermissionDenied
        return recipient

    def form_valid(self, form):
        current_subscriptions = self.object.subscriptions
        current_unsubscriptions = self.object.unsubscriptions.all()

        # Add new unsubscriptions
        for email in current_subscriptions:
            if email not in form.cleaned_data['subscribed_emails']:
                email.unsubscriptions.add(self.object)

        # Add new subscriptions
        for email in form.cleaned_data['subscribed_emails']:
            if email in current_unsubscriptions:
                email.unsubscriptions.remove(self.object)

        return super(RecipientSubscriptionsUpdateView, self).form_valid(form)

    def get_success_url(self):
        messages.success(self.request,
                         'Your subscriptions have been successfully updated.')
        return self.object.unsubscribe_url


class SettingListView(SettingsMixin, ListView):
    model = Setting
    template_name = 'manager/settings.html'
    context_object_name = 'settings'
    pageinate_by = 20


class SettingCreateView(SettingsMixin, CreateView):
    model = Setting
    template_name = 'manager/setting-create.html'
    form_class = SettingCreateUpdateForm

    def form_valid(self, form):
        messages.success(self.request, 'Setting successfully created.')
        return super(SettingCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('manager-setting-update',
                       args=(),
                       kwargs={'pk': self.object.pk})


class SettingUpdateView(SettingsMixin, UpdateView):
    model = Setting
    template_name = 'manager/setting-update.html'
    form_class = SettingCreateUpdateForm

    def form_valid(self, form):
        messages.success(self.request, 'Setting successfully updated.')
        return super(SettingUpdateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('manager-setting-update',
                       args=(),
                       kwargs={'pk': self.object.pk})


class SettingDeleteView(SettingsMixin, DeleteView):
    model = Setting
    template_name = 'manager/setting-delete.html'
    template_name_suffix = '-delete-confirm'

    def get_success_url(self):
        messages.success(self.request, 'Setting successfully deleted.')
        return reverse('manager-settings')


##
# Tracking
##
def redirect(request):
    '''
        Redirects based on URL and records URL click
    '''
    instance_id = request.GET.get('instance',  None)
    url_string = request.GET.get('url',       None)
    position = request.GET.get('position',  None)
    recipient_id = request.GET.get('recipient', None)
    mac = request.GET.get('mac',       None)

    if not url_string:
        pass # Where do we go?
    else:
        url_string = urllib.unquote(url_string)
        # No matter what happens, make sure the redirection works
        try:
            if position and recipient_id and mac and instance_id:
                try:
                    position = int(position)
                    recipient_id = int(recipient_id)
                    instance_id = int(instance_id)
                except ValueError:
                    log.error('value error')
                    pass
                else:
                    if mac == calc_url_mac(url_string,
                                           position,
                                           recipient_id,
                                           instance_id):
                        try:
                            recipient = Recipient.objects.get(id=recipient_id)
                            instance = Instance.objects.get(id=instance_id)
                            url = URL.objects.get(name=url_string,
                                                  position=position,
                                                  instance=instance)
                        except URL.DoesNotExist:
                            # This should have been created
                            # in the mailer-process command
                            # when this email was sent
                            pass
                        except Recipient.DoesNotExist:
                            # strange
                            log.error('bad recipient')
                            pass
                        except Instance.DoesNotExist:
                            # also strange
                            log.error('bad instance')
                            pass
                        else:
                            url_click = URLClick(recipient=recipient, url=url)
                            url_click.save()
                            log.debug('url click saved')
                    else:
                        log.error('wrong mac')
            else:
                log.error('something none')
        except Exception, e:
            log.error(str(e))
            pass
        return HttpResponseRedirect(url_string)


def instance_open(request):
    '''
        Records an email open
    '''
    instance_id = request.GET.get('instance',  None)
    recipient_id = request.GET.get('recipient', None)
    mac = request.GET.get('mac',       None)

    if recipient_id and mac and instance_id is not None:
        try:
            instance_id = int(instance_id)
            recipient_id = int(recipient_id)
        except ValueError:
            # corrupted
            pass
        else:
            if mac == calc_open_mac(recipient_id, instance_id):
                try:
                    recipient = Recipient.objects.get(id=recipient_id)
                    instance = Instance.objects.get(id=instance_id)
                    InstanceOpen.objects.get(recipient=recipient,
                                             instance=instance)
                except Recipient.DoesNotExist:
                    # strange
                    log.error('bad recipient')
                    pass
                except Instance.DoesNotExist:
                    # also strange
                    log.error('bad instance')
                    pass
                except InstanceOpen.DoesNotExist:
                    instance_open = InstanceOpen(recipient=recipient,
                                                 instance=instance)
                    instance_open.save()
                    log.debug('open saved')
    return HttpResponse(settings.DOT, content_type='image/png')

##
# Utility Views
##
class RecipientCSVImportView(RecipientsMixin, FormView):
    template_name = 'manager/recipient-csv-import.html'
    form_class = RecipientCSVImportForm

    def form_valid(self, form):
        if form.is_valid():
            existing_group_name = None

            if form.cleaned_data['existing_group_name']:
                existing_group_name = form.cleaned_data['existing_group_name'].name

            new_group_name = form.cleaned_data['new_group_name']
            column_order = list(col.strip() for col in form.cleaned_data['column_order'].split(','))
            print column_order
            skip_first_row = form.cleaned_data['skip_first_row']
            csv_file = form.cleaned_data['csv_file']

            group = ""
            if existing_group_name is not None:
                group = existing_group_name
            else:
                group = new_group_name

            try:
                importer = CSVImport(csv_file, group, skip_first_row, column_order)
                importer.import_emails()
            except Exception, e:
                form._errors['__all__'] = ErrorList([str(e)])
                return super(RecipientCSVImportView, self).form_invalid(form)

            messages.success(self.request, 'Emails successfully imported.')
            return super(RecipientCSVImportView, self).form_valid(form)

    def get_success_url(self):
        return reverse('manager-recipientgroups')
