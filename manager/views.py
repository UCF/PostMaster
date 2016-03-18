from datetime import date
from datetime import datetime
import time
import logging
import os
from util import calc_open_mac
from util import calc_unsubscribe_mac
from util import calc_unsubscribe_mac_old
from util import calc_url_mac
import urllib
import urlparse
import json

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import EmptyPage
from django.core.paginator import PageNotAnInteger
from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views.generic.base import TemplateView
from django.views.generic.base import View
from django.views.generic.edit import CreateView
from django.views.generic.edit import DeleteView
from django.views.generic.edit import FormView
from django.views.generic.edit import UpdateView
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.forms.util import ErrorList

from manager.forms import EmailSearchForm
from manager.forms import EmailCreateUpdateForm
from manager.forms import EmailInstantSendForm
from manager.forms import PreviewInstanceLockForm
from manager.forms import RecipientAttributeCreateForm
from manager.forms import RecipientAttributeUpdateForm
from manager.forms import RecipientAttributeFormSet
from manager.forms import RecipientCreateUpdateForm
from manager.forms import RecipientCSVImportForm
from manager.forms import RecipientGroupSearchForm
from manager.forms import RecipientGroupCreateUpdateForm
from manager.forms import RecipientSearchForm
from manager.forms import RecipientSubscriptionsForm
from manager.forms import SettingCreateUpdateForm
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
from manager.litmusapi import LitmusApi
from manager.utils import CSVImport
from manager.utils import EmailSender
from manager.utils import AmazonS3Helper


log = logging.getLogger(__name__)


##
# Mixins
##
class SortSearchMixin(object):
    def get_queryset(self):
        queryset = super(SortSearchMixin, self).get_queryset();

        # sort parameter
        self._sort = 'asc'
        self._order = 'asc'
        self._search_query = ''

        if self.request.GET.get('sort'):
            self._sort = self.request.GET.get('sort')

        if self.request.GET.get('order'):
            self._order = self.request.GET.get('order')

        if self.request.GET.get('search_query'):
            self._search_query = self.request.GET.get('search_query')

        # search parameter (search_form defined in View)
        self._search_valid = self.search_form.is_valid()

        if self._search_valid:
            kwargs = {
                '{0}__icontains'.format(self.search_field): self.search_form.cleaned_data['search_query']
            }
            queryset = queryset.filter(**kwargs)

        if self._sort:
            queryset.order_by(self._sort)
            if self._order == 'des':
                self._order = 'asc'
                return queryset.reverse()
            else:
                self._order = 'des'
                return queryset
        else:
            return queryset

    def get_context_data(self, **kwargs):
        context = super(SortSearchMixin, self).get_context_data(**kwargs)
        context['sort'] = self._sort
        context['order'] = self._order
        context['search_query'] = self._search_query
        return context

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

        try:
            instances = Instance.objects.filter(end=None, send_terminate=False)
        except Instance.DoesNotExist:
            instances = None

        context['instances'] = instances

        return context


##
# Emails
##
class EmailListView(EmailsMixin, SortSearchMixin, ListView):
    model = Email
    template_name = 'manager/emails.html'
    context_object_name = 'emails'
    paginate_by = 20

    def get_queryset(self):
        self.search_field = 'title'
        self.search_form = EmailSearchForm(self.request.GET)
        emails = super(EmailListView, self).get_queryset()
        return emails

    def get_context_data(self, **kwargs):
        context = super(EmailListView, self).get_context_data(**kwargs)
        context['search_form'] = self.search_form
        context['search_valid'] = self._search_valid
        return context


class EmailCreateView(EmailsMixin, CreateView):
    model = Email
    template_name = 'manager/email-create.html'
    form_class = EmailCreateUpdateForm

    def form_valid(self, form):
        email = form.instance
        form.instance.creator = self.request.user

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

        email.updated_at = now
        messages.success(self.request, 'Email successfully updated.')
        return super(EmailUpdateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('manager-email-update',
                       args=(),
                       kwargs={'pk': self.object.pk})


class EmailPlaceholderVerificationView(EmailsMixin, DetailView):
    model = Email
    template_name = 'manager/email-placeholder-verification.html'

    def get_context_data(self, **kwargs):
        context = super(EmailPlaceholderVerificationView, self).get_context_data(**kwargs)
        placeholders = self.object.placeholders
        context['attributes'] = []
        for placeholder in placeholders:
            emails = self.object.recipients.exclude(attributes__name=placeholder)
            if emails.count > 0:
                context['attributes'].append((placeholder, emails[:10], emails.count))
        return context


class EmailInstantSendView(EmailsMixin, FormView):
    template_name = 'manager/email-instant-send.html'
    form_class = EmailInstantSendForm

    def form_valid(self, form):
        subject = form.cleaned_data['subject']
        source_html_uri = form.cleaned_data['source_html_uri']
        from_email_address = form.cleaned_data['from_email_address']
        from_friendly_name = form.cleaned_data['from_friendly_name']
        replace_delimiter = form.cleaned_data['replace_delimiter']
        recipient_groups = form.cleaned_data['recipient_groups']

        email = Email()
        email.subject = subject
        email.source_html_uri = source_html_uri
        email.from_email_address = from_email_address
        email.from_friendly_name = from_friendly_name
        email.replace_delimiter = replace_delimiter
        email.preview = False

        recipients = []
        for recipient_group in recipient_groups.all():
            for recipient in recipient_group.recipients.all():
                recipients.append(recipient)

        sender = EmailSender(email, recipients)

        try:
            sender.send()
        except Exception, e:
            form._errors['__all__'] = ErrorList([str(e)])
            return super(EmailInstantSendView, self).form_invalid(form)
        else:
            messages.success(self.request, 'Emails successfully sent.')
            return super(EmailInstantSendView, self).form_valid(form)

    def get_success_url(self):
        messages.success(self.request, 'Email sent')
        return reverse('manager-emails')


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


class PreviewInstanceListView(EmailsMixin, ListView):
    model = PreviewInstance
    template_name = 'manager/email-preview-instances.html'
    paginate_by = 20
    context_object_name = 'preview_instances'

    def dispatch(self, request, *args, **kwargs):
        self._email = get_object_or_404(Email, pk=kwargs['pk'])
        return super(PreviewInstanceListView, self).dispatch(request,
                                                             *args,
                                                             **kwargs)

    def get_queryset(self):
        return PreviewInstance.objects.filter(email=self._email)

    def get_context_data(self, **kwargs):
        context = super(PreviewInstanceListView, self). \
            get_context_data(**kwargs)
        context['email'] = self._email
        return context


class LockContentView(UpdateView):
    model = PreviewInstance
    form_class = PreviewInstanceLockForm

    def get_success_url(self):
        """
        Return the user to the preview instances list for the parent email
        """
        # theobject = self.object.lock_content
        # blah = self.object.pk
        # raise Exception
        return reverse('manager-email-preview-instances',
                       args=(self.object.email.pk,))


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

    def get_context_data(self, **kwargs):
        """
        Add the thumbnail preview to the context data
        """
        context = super(InstanceDetailView, self).get_context_data(**kwargs)
        if self.object.litmus_id:
            litmus = LitmusApi(settings.LITMUS_BASE_URL,
                               settings.LITMUS_USER,
                               settings.LITMUS_PASS,
                               settings.LITMUS_TIMEOUT,
                               settings.LITMUS_VERIFY)
            xml_test = litmus.get_test(self.object.litmus_id)
            desktop_images = litmus.get_image_urls('ol2015',
                                                   xml=xml_test)
            mobile_images = litmus.get_image_urls('iphone6',
                                                  xml=xml_test)
            if desktop_images is not None:
                context['desktop_thumbnail_image'] = desktop_images['thumbnail_url']
                context['desktop_full_image'] = desktop_images['full_url']

            if mobile_images is not None:
                context['mobile_thumbnail_image'] = mobile_images['thumbnail_url']
                context['mobile_full_image'] = mobile_images['full_url']

            context['litmus_url'] = settings.LITMUS_BASE_URL + \
                LitmusApi.TESTS + self.object.litmus_id

        return context


def instance_cancel(request, pk):
    retval= {}

    # get the instance id
    if request.POST:
        instance_id = request.POST['email-instance-id']
    else:
        instance_id = pk

    if instance_id:
        try:
            instance = Instance.objects.get(pk=instance_id)

            if not instance.end:
                instance.send_terminate = True
                instance.save()
                retval['message'] = "Email instance send_terminate set to true."
            else:
                retval['message'] = "Email instance send has already ended, set_terminate left unchanged."

            retval['success'] = True
        except Instance.DoesNotExist:
            retval['success'] = False
            retval['error'] = {}
            retval['error']['code'] = 404
            retval['error']['message'] = "Email instance does not exist"

    return HttpResponse(json.dumps(retval), content_type='application/json')


class EmailDesignView(TemplateView):
    template_name = 'manager/email-design.html'

    def get_context_data(self, **kwargs):
        context = super(EmailDesignView, self).get_context_data(**kwargs)
        templates_path = 'email-templates/'
        s3 = AmazonS3Helper()

        project_url = settings.PROJECT_URL
        project_url_agnostic = project_url.replace('http://', '//')
        context['email_templates_url'] = project_url_agnostic + settings.MEDIA_URL + templates_path
        context['email_templates'] = os.listdir(settings.MEDIA_ROOT + '/' + templates_path)
        context['froala_license'] = settings.FROALA_EDITOR_LICENSE
        context['valid_key_path'] = s3.get_base_key_path_url()
        return context


##
# Recipients Groups
##
class RecipientGroupListView(RecipientGroupsMixin, SortSearchMixin, ListView):
    model = RecipientGroup
    template_name = 'manager/recipientgroups.html'
    context_object_name = 'groups'
    paginate_by = 20

    def get_queryset(self):
        self.search_field = 'name'
        self.search_form = RecipientGroupSearchForm(self.request.GET)
        recipient_groups = super(RecipientGroupListView, self).get_queryset()
        return recipient_groups

    def get_context_data(self, **kwargs):
        context = super(RecipientGroupListView, self).get_context_data(**kwargs)
        context['search_form'] = self.search_form
        context['search_valid'] = self._search_valid
        return context


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

    def get_context_data(self, **kwargs):
        context = super(RecipientGroupUpdateView, self).get_context_data(**kwargs)
        recipient_group = RecipientGroup.objects.get(pk=self.object.pk)
        recipients = recipient_group.recipients.all()
        paginator = Paginator(recipients, 20)

        page = self.request.GET.get('page')
        try:
            context['recipients'] = paginator.page(page)
        except PageNotAnInteger:
            context['recipients'] = paginator.page(1)
        except EmptyPage:
            context['recipients'] = paginator.page(paginator.num_pages)

        return context

    def form_valid(self, form):
        recipient_email = self.request.POST.get('recipient-email')

        if recipient_email:
            recipient_group = RecipientGroup.objects.get(pk=self.object.pk)
            try:
                recipient = Recipient.objects.get(email_address=recipient_email)
                if recipient not in recipient_group.recipients.all():
                    recipient_group.recipients.add(recipient)
                    recipient_group.save()
                else:
                    messages.warning(self.request, 'Recipient %s already in %s.' % (recipient_email, recipient_group.name))
            except Recipient.DoesNotExist:
                recipient = Recipient(email_address=recipient_email)
                recipient.save()
                recipient_group.recipients.add(recipient)
                recipient_group.save()
                messages.success(self.request, 'Recipient %s successfully created and added to %s.' % (recipient_email, recipient_group.name))
                return super(RecipientGroupUpdateView, self).form_valid(form)
            except Exception, e:
                message.errors(self.request, 'An error occurred: %s', e.strerror)
                return super(RecipientGroupUpdateView, self).form_invalid(form)

        messages.success(self.request, 'Recipient group successfully updated.')
        return super(RecipientGroupUpdateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('manager-recipientgroup-update',
                       args=(),
                       kwargs={'pk': self.object.pk})

class RecipientGroupDeleteView(RecipientGroupsMixin, DeleteView):
    model = RecipientGroup
    template_name = 'manager/recipientgroup-delete-confirm.html'

    def get_context_data(self, **kwargs):
        context = super(RecipientGroupDeleteView, self).get_context_data(**kwargs)
        recurring_emails = Email.objects.filter(active=True, recipient_groups__id=self.object.pk).exclude(recurrence=0)
        upcoming_emails = Email.objects.filter(active=True, start_date__gt=datetime.now(), recurrence=0)
        context['recurring_emails'] = recurring_emails
        context['upcoming_emails'] = upcoming_emails
        return context

    def get_success_url(self):
        return reverse('manager-recipientgroups')

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
            return Recipient.objects.all().order_by('disable', 'email_address')

    def get_context_data(self, **kwargs):
        context = super(RecipientListView, self).get_context_data(**kwargs)
        context['search_form'] = self._search_form
        context['search_valid'] = self._search_valid
        context['search_query'] = self._search_form.cleaned_data['email_address'] if self._search_valid else ''
        return context


class RecipientCreateView(RecipientsMixin, CreateView):
    model = Recipient
    template_name = 'manager/recipient-create.html'
    context_object_name = 'recipient'
    form_class = RecipientCreateUpdateForm

    def get(self, request, *args, **kwargs):
        self.object = None
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        recipient_attributes_formset = RecipientAttributeFormSet()
        return self.render_to_response(
            self.get_context_data(form=form, recipient_attributes_formset=recipient_attributes_formset))

    def post(self, request, *args, **kwargs):
        self.object = None
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        recipient_attributes_formset = RecipientAttributeFormSet(self.request.POST)
        if (form.is_valid() and recipient_attributes_formset.is_valid()):
            return self.form_valid(form, recipient_attributes_formset)
        else:
            return self.form_invalid(form, recipient_attributes_formset)

    def form_valid(self, form, recipient_attributes_formset):
        self.object = form.save()
        recipient_attributes_formset.instance = self.object
        recipient_attributes_formset.save()
        messages.success(self.request, 'Recipient successfully created.')
        self.object.set_groups(form.cleaned_data['groups'])
        return super(RecipientCreateView, self).form_valid(form)

    def form_invalid(self, form, recipient_attributes_formset):
        messages.error(self.request, 'Please review the errors below and try again.')
        return self.render_to_response(
            self.get_context_data(form=form, recipient_attributes_formset=recipient_attributes_formset))

    def get_success_url(self):
        return reverse('manager-recipient-update',
                       args=(),
                       kwargs={'pk': self.object.pk})


class RecipientUpdateView(RecipientsMixin, UpdateView):
    model = Recipient
    template_name = 'manager/recipient-update.html'
    form_class = RecipientCreateUpdateForm
    form_attributes_class = RecipientAttributeCreateForm

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        recipient_attributes_formset = RecipientAttributeFormSet(instance=self.object)
        return self.render_to_response(
            self.get_context_data(form=form, recipient_attributes_formset=recipient_attributes_formset))

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        recipient_attributes_formset = RecipientAttributeFormSet(self.request.POST, instance=self.object)
        if (form.is_valid() and recipient_attributes_formset.is_valid()):
            return self.form_valid(form, recipient_attributes_formset)
        else:
            return self.form_invalid(form, recipient_attributes_formset)

    def form_valid(self, form, recipient_attributes_formset):
        self.object = form.save()
        recipient_attributes_formset.instance = self.object
        recipient_attributes_formset.save()
        messages.success(self.request, 'Recipient successfully updated.')
        self.object.set_groups(form.cleaned_data['groups'])
        return super(RecipientUpdateView, self).form_valid(form)

    def form_invalid(self, form, recipient_attributes_formset):
        messages.error(self.request, 'Please review the errors below and try again.')
        return self.render_to_response(
            self.get_context_data(form=form, recipient_attributes_formset=recipient_attributes_formset))

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
        email_id = self.request.GET.get('email', None)

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
    instance_id = request.GET.get('instance', None)
    url_string = request.GET.get('url', None)
    position = request.GET.get('position', None)
    recipient_id = request.GET.get('recipient', None)
    mac = request.GET.get('mac', None)

    if not url_string:
        pass  # Where do we go?
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
    instance_id = request.GET.get('instance', None)
    recipient_id = request.GET.get('recipient', None)
    mac = request.GET.get('mac', None)

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

                    instance_open, created = InstanceOpen.objects.get_or_create(recipient=recipient, instance=instance, is_reopen=False)
                    if not created:
                        instance_new = InstanceOpen(recipient=recipient, instance=instance, is_reopen=True)
                        instance_new.save()
                        log.debug('re-open created')
                    else:
                        log.debug('open created')
                except InstanceOpen.MultipleObjectsReturned:
                    log.error('multiple objects returned');
                    pass
                except Recipient.DoesNotExist:
                    # strange
                    log.error('bad recipient')
                    pass
                except Instance.DoesNotExist:
                    # also strange
                    log.error('bad instance')
                    pass
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


def instance_json_feed(request):
    retval = {}

    def datetime_to_milliseconds(datetime_object):
        if datetime_object:
            return time.mktime(datetime_object.timetuple()) * 1000
        else:
            return 0

    if request.GET.get('pk'):
        pk = request.GET.get('pk')
        try:
            instance = Instance.objects.get(pk=pk)

            retval['sent_count'] = instance.sent_count
            retval['total'] = instance.recipient_details.count()
            retval['start'] = datetime_to_milliseconds(instance.start)
            retval['end'] = datetime_to_milliseconds(instance.end)
        except Instance.DoesNotExist:
            retval['error'] ='Error getting instance send information.'
            pass

    return HttpResponse(json.dumps(retval), content_type='application/json')


def recipient_json_feed(request):
    search_term = ''

    if request.GET.get('search'):
        search_term = request.GET.get('search')

    recipients = []

    if search_term:
        recipient_fks = list(RecipientAttribute.objects.filter(name__in=['First Name','Last Name','Preferred Name'], value__contains=search_term).values_list('recipient', flat=True).distinct())
        recipient_emails = list(Recipient.objects.filter(email_address__contains=search_term).values_list('pk', flat=True))

        for r in recipient_emails:
            if r not in recipient_fks:
                recipient_fks.append(r)

        for r in recipient_fks:
            recipients.append(Recipient.objects.get(pk=r))

    else:
        recipients = Recipient.objects.all()

    retval = []

    for recipient in recipients:
        first_name = RecipientAttribute.objects.filter(recipient=recipient, name='First Name')[0].value if RecipientAttribute.objects.filter(recipient=recipient, name='First Name') else ''
        last_name = RecipientAttribute.objects.filter(recipient=recipient, name='Last Name')[0].value if RecipientAttribute.objects.filter(recipient=recipient, name='Last Name') else ''
        preferred_name = RecipientAttribute.objects.filter(recipient=recipient, name='Preferred Name')[0].value if RecipientAttribute.objects.filter(recipient=recipient, name='Preferred Name') else ''

        r = {}
        r['pk'] = recipient.pk
        r['email_address'] = recipient.email_address
        r['first_name'] = first_name
        r['last_name'] = last_name
        r['preferred_name'] = preferred_name

        retval.append(r)

    return HttpResponse(json.dumps(retval), content_type='application/json')

##
# Creates a recipient group based on email opens.
# POST only
##
def create_recipient_group_email_opens(request):
    '''
    Creates a recipient group based on email opens.
    POST only
    '''
    email_instance_id = request.POST.get('email-instance-id')
    email_instance = Instance.objects.get(pk=email_instance_id)
    recipients = InstanceOpen.objects.filter(instance=email_instance_id).values_list('recipient')

    recipient_group = RecipientGroup(name=email_instance.email.title + ' Recipient Group ' + datetime.now().strftime('%m-%d-%y %I:%M %p'))
    if RecipientGroup.objects.filter(name=recipient_group.name).count() > 0:
        recipient_group.name = recipient_group.name + ' - 1'

    recipient_group.save()

    for recipient in recipients:
        recipient_group.recipients.add(recipient[0])

    recipient_group.save()

    messages.success(request, 'Recipient group successfully created. Please remember to update the name to something unique.')
    return HttpResponseRedirect(
        reverse('manager-recipientgroup-update',
            args=(),
            kwargs={'pk': recipient_group.pk}
        )
    )

def create_recipient_group_url_clicks(request):
    '''
        Creates a recipient group based on url clicks.
        POST only
    '''
    url_ids = request.POST.getlist('url-pks[]')
    url_clicks = []
    for url_id in url_ids:
        url_clicks.append(URLClick.objects.filter(url=url_id))

    recipient_group = RecipientGroup(name='URL Click Recipient Group - ' + datetime.now().strftime('%m-%d-%y %I:%M %p'))
    recipient_group.save()

    for url_click in url_clicks:
        for click in url_click:
            if click.recipient not in recipient_group.recipients.all():
                recipient_group.recipients.add(click.recipient)

    #recipient_group.save()

    messages.success(request, 'Recipient group successfully created. Please remember to update the name to something unique.')
    return HttpResponseRedirect(
        reverse('manager-recipientgroup-update',
            args=(),
            kwargs={'pk': recipient_group.pk}
        )
    )


def s3_upload_user_file(request):
    """
    Uploads a unique file to Amazon S3, using a key prefixed with the current
    user's username.

    Returns json containing uploaded file url ( {link: '...'} ) or error
    message ( {error: '...'} ).

    Note: returned json must follow this format to play nicely with the Froala
    image uploader.
    """
    if request.method == 'POST':
        response_data = {}
        file = request.FILES['file']
        file_prefix = request.user.username + '/'
        protocol = request.POST.get('protocol')
        extension_groupname = request.POST.get('extension_groupname')
        unique = request.POST.get('unique')
        s3 = AmazonS3Helper()

        if file_prefix is None:
            file_prefix = ''

        if protocol not in s3.valid_protocols:
            protocol = '//'

        # convert to bool
        if not unique:
            unique = False
        else:
            unique = True

        if file is None:
            response_data['error'] = 'File not set.'
        else:
            try:
                keyobj = s3.upload_file(
                    file=file,
                    unique=unique,
                    file_prefix=file_prefix,
                    extension_groupname=extension_groupname
                )
            except AmazonS3Helper.KeyCreateError, e:
                response_data['error'] = 'Failed to upload file.'
            except PermissionDenied:
                response_data['error'] = 'Cannot upload this type of file.'

            try:
                url = keyobj.generate_url(0, query_auth=False, force_http=True)
            except Exception, e:
                response_data['error'] = 'Failed to generate url for file.'

            if url:
                if protocol != 'http://':
                    url = url.replace('http://', protocol)
                response_data['link'] = url

        return HttpResponse(
            json.dumps(response_data),
            mimetype='application/json'
        )
    else:
        return HttpResponseForbidden()


def s3_get_user_files(request):
    """
    Returns json array of a user's files' urls in S3 bucket.
    """
    if request.method == 'GET':
        response_data = {}
        protocol = request.GET.get('protocol')
        file_prefix = request.user.username + '/'
        extension_groupname = request.GET.get('extension_groupname')
        s3 = AmazonS3Helper()

        if protocol not in s3.valid_protocols:
            protocol = 'http://'

        try:
            key_list = s3.get_file_list(file_prefix, extension_groupname)
            url_list = []

            for keyobj in key_list:
                url = keyobj.generate_url(0, query_auth=False, force_http=True)

                if url:
                    if protocol != 'http://':
                        url = url.replace('http://', protocol)

                    url_list.append(url)

            response_data = url_list
        except AmazonS3Helper.KeylistFetchError, e:
            response_data['error'] = 'Failed to retrieve user file list.'

        return HttpResponse(
            json.dumps(response_data),
            mimetype='application/json'
        )
    else:
        return HttpResponseForbidden()


def s3_delete_user_file(request):
    """
    Deletes a file from Amazon S3 by its url.

    Returns json containing success message ( {message: '...'} ) or error
    message ( {error: '...'} ).

    Note: returned json must follow this format to play nicely with the Froala
    image uploader.
    """
    if request.method == 'POST':
        response_data = {}
        file_prefix = request.user.username + '/'
        file_src = request.POST.get('src')  # url of file
        s3 = AmazonS3Helper()

        if file_src is None:
            response_data['error'] = 'No file source set.'
        else:
            # Get the filename from file_src url
            filename = os.path.basename(urlparse.urlsplit(file_src).path)

            keyname = s3.base_key_path + file_prefix + filename

            try:
                keyobj = s3.delete_file(keyname)
                response_data['message'] = 'File successfully deleted.'
            except AmazonS3Helper.InvalidKeyError, e:
                response_data['error'] = str(e)
            except AmazonS3Helper.KeyDeleteError, e:
                response_data['error'] = 'Failed to delete file.'

        return HttpResponse(
            json.dumps(response_data),
            mimetype='application/json'
        )
    else:
        return HttpResponseForbidden()
