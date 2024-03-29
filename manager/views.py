from datetime import date
from datetime import datetime
import time
import logging
import os
from util import calc_open_mac
from util import calc_unsubscribe_mac
from util import calc_unsubscribe_mac_old
from util import calc_url_mac
import urllib.request, urllib.parse, urllib.error
from urllib.parse import urlparse
import json
import subprocess
import sys
import csv
from html.parser import HTMLParser

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import EmptyPage
from django.core.paginator import PageNotAnInteger
from django.core.paginator import Paginator
from django.urls import reverse
from django.db.models import Max, Min, Q
from django.http import HttpResponse
from django.http import HttpResponseForbidden
from django.http import HttpResponseRedirect
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.views.generic.base import TemplateView
from django.views.generic.base import View
from django.views.generic.edit import CreateView
from django.views.generic.edit import DeleteView
from django.views.generic.edit import FormView
from django.views.generic.edit import UpdateView
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.forms.utils import ErrorList
from django.contrib.staticfiles.storage import staticfiles_storage

from manager.forms import CampaignForm
from manager.forms import EmailSearchForm
from manager.forms import EmailCreateUpdateForm
from manager.forms import EmailInstantSendForm
from manager.forms import ExportCleanupForm
from manager.forms import PreviewInstanceLockForm
from manager.forms import RecipientAttributeCreateForm
from manager.forms import RecipientAttributeUpdateForm
from manager.forms import RecipientAttributeFormSet
from manager.forms import RecipientCreateUpdateForm
from manager.forms import RecipientCSVImportForm
from manager.forms import RecipientGroupSearchForm
from manager.forms import RecipientGroupCreateForm
from manager.forms import RecipientGroupUpdateForm
from manager.forms import RecipientSearchForm
from manager.forms import RecipientSubscriptionsForm
from manager.forms import SegmentForm
from manager.forms import IncludeSegmentRuleFormset
from manager.forms import ExcludeSegmentRuleFormset
from manager.forms import SettingCreateUpdateForm
from manager.forms import SubscriptionCategoryForm
from manager.models import Campaign
from manager.models import Email
from manager.models import Instance
from manager.models import InstanceOpen
from manager.models import PreviewInstance
from manager.models import RecipientAttribute
from manager.models import Recipient
from manager.models import RecipientGroup
from manager.models import Segment
from manager.models import SegmentRule
from manager.models import Setting
from manager.models import StaleRecord
from manager.models import SubprocessStatus
from manager.models import SubscriptionCategory
from manager.models import URL
from manager.models import URLClick
from manager.utilities.email_sender import EmailSender
from manager.utilities.s3_helper import AmazonS3Helper


log = logging.getLogger(__name__)


##
# Mixins
##
class SortSearchMixin(object):
    def get_queryset(self):
        queryset = super(SortSearchMixin, self).get_queryset()

        # sort parameter
        self._sort = None
        self._order = None
        self._order_change = 'asc'
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

        if self._sort and self._order == 'des':
            self._order_change = 'asc'
            return queryset.order_by('-{0}'.format(self._sort))
        elif self._sort and self._order == 'asc':
            self._order_change = 'des'
            return queryset.order_by(self._sort)
        else:
            return queryset

    def generate_query_params(self, page, previous = True):
        query_mappings = {}

        if previous and page and page.has_previous():
            query_mappings['page'] = page.previous_page_number()

        if not previous and page and page.has_next():
            query_mappings['page'] = page.next_page_number()

        if self._search_query and self._search_query != '':
            query_mappings['search_query'] = self._search_query

        if self._sort and self._sort != '':
            query_mappings['sort'] = self._sort

        if self._order and self._order != '':
            query_mappings['order'] = self._order

        return '?{0}'.format(urllib.parse.urlencode(query_mappings))

    def get_context_data(self, **kwargs):
        context = super(SortSearchMixin, self).get_context_data(**kwargs)
        context['sort'] = self._sort
        context['order_change'] = self._order_change
        context['search_query'] = self._search_query

        query_mapping = {}

        if 'page_obj' in context:
            page = context['page_obj']

            if page and page.has_previous():
                context['previous_url'] = self.generate_query_params(page, True)

            if page and page.has_next():
                context['next_url'] = self.generate_query_params(page, False)

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


class SubscriptionsMixin(object):
    def get_context_data(self, **kwargs):
        context = super(SubscriptionsMixin, self).get_context_data(**kwargs)
        context['section'] = 'subscriptions'
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

        upcoming_emails = Email.objects.sending_this_week()
        context['upcoming_emails'] = upcoming_emails

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

    def get_form(self, form_class=None):
        form = super(EmailUpdateView, self).get_form(form_class)
        email = form.instance
        if email is not None:
            selected_recipient_groups = email.recipient_groups.all()
            active_recipient_groups = form.fields['recipient_groups'].queryset
            # Always show all selected recipient groups for the email,
            # even if the group(s) have been archived:
            valid_recipient_groups = (active_recipient_groups | selected_recipient_groups).distinct()
            form.fields['recipient_groups'].queryset = valid_recipient_groups
        return form

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
            if len(emails) > 0:
                context['attributes'].append((placeholder, emails[:10], len(emails)))
        return context


class EmailInstantSendView(EmailsMixin, FormView):
    template_name = 'manager/email-instant-send.html'
    form_class = EmailInstantSendForm

    def get_initial(self):
        initial = super(EmailInstantSendView, self).get_initial()

        if 'email_id' in self.request.GET:
            email = Email.objects.get(pk=self.request.GET.get('email_id'))
            initial['subject'] = "**TEST** " + email.subject + " **TEST**"
            initial['source_html_uri'] = email.source_html_uri
            initial['from_email_address'] = email.from_email_address
            initial['from_friendly_name'] = email.from_friendly_name
            initial['replace_delimiter'] = email.replace_delimiter

        return initial

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
        except Exception as e:
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
    template_name = 'manager/email-delete-confirm.html'
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


##
# Recipients Groups
##
class RecipientGroupBaseListView(RecipientGroupsMixin, SortSearchMixin, ListView):
    model = RecipientGroup
    template_name = 'manager/recipientgroups.html'
    context_object_name = 'groups'
    paginate_by = 20

    def get_queryset(self):
        self.search_field = 'name'
        self.search_form = RecipientGroupSearchForm(self.request.GET)
        recipient_groups = super(RecipientGroupBaseListView, self).get_queryset()
        if not self.request.GET.get('status') or self.request.GET.get('status') == 'Active':
            recipient_groups = recipient_groups.filter(archived=False)
        elif self.request.GET.get('status') == 'Archived':
            recipient_groups = recipient_groups.filter(archived=True)
        return recipient_groups

    def get_context_data(self, **kwargs):
        context = super(RecipientGroupBaseListView, self).get_context_data(**kwargs)
        context['search_form'] = self.search_form
        context['search_valid'] = self._search_valid
        context['status'] = 'Active' if not self.request.GET.get(
            'status') else self.request.GET.get(
            'status')
        return context


class RecipientGroupLiveListView(RecipientGroupBaseListView):
    def get_queryset(self):
        recipient_groups = super(RecipientGroupLiveListView, self).get_queryset()
        recipient_groups = recipient_groups.filter(preview=False)
        return recipient_groups

    def get_context_data(self, **kwargs):
        context = super(RecipientGroupLiveListView,
                        self).get_context_data(**kwargs)
        context['preview'] = False
        return context


class RecipientGroupPreviewListView(RecipientGroupBaseListView):
    def get_queryset(self):
        recipient_groups = super(RecipientGroupPreviewListView, self).get_queryset()
        recipient_groups = recipient_groups.filter(preview=True)
        return recipient_groups

    def get_context_data(self, **kwargs):
        context = super(RecipientGroupPreviewListView,
                        self).get_context_data(**kwargs)
        context['preview'] = True
        return context


class RecipientGroupCreateView(RecipientGroupsMixin, CreateView):
    model = RecipientGroup
    template_name = 'manager/recipientgroup-create.html'
    form_class = RecipientGroupCreateForm

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
    form_class = RecipientGroupUpdateForm

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
            except Exception as e:
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
# Segments
##

class SegmentListView(ListView):
    model = Segment
    template_name = 'manager/segments-list.html'
    context_object_name = 'segments'
    paginate_by = 20

class SegmentCreateView(CreateView):
    model = Segment
    form_class = SegmentForm
    template_name = 'manager/segments-create.html'

    def get_context_data(self, **kwargs):
        data = super(SegmentCreateView, self).get_context_data(**kwargs)
        if self.request.POST:
            data['include_rules'] = IncludeSegmentRuleFormset(
                self.request.POST,
                prefix='include_rules'
            )
            data['exclude_rules'] = ExcludeSegmentRuleFormset(
                self.request.POST,
                prefix='exclude_rules'
            )
        else:
            data['include_rules'] = IncludeSegmentRuleFormset(
                prefix='include_rules'
            )
            data['exclude_rules'] = ExcludeSegmentRuleFormset(
                prefix='exclude_rules'
            )

        return data

    def form_valid(self, form):
        self.object = form.save()
        context = self.get_context_data(form=form)
        include_formset = context['include_rules']
        exclude_formset = context['exclude_rules']

        if include_formset.is_valid() and exclude_formset.is_valid():
            response = super(SegmentCreateView, self).form_valid(form)
            for idx, subform in enumerate(include_formset.forms):
                cleaned_data = subform.cleaned_data
                if cleaned_data:
                    rule = SegmentRule(
                        segment=self.object,
                        rule_type='include',
                        field=cleaned_data['field'],
                        conditional='AND' if idx == 0 else cleaned_data['conditional'],
                        key=None if cleaned_data['field'] not in ['has_attribute', 'clicked_url_in_instance'] else cleaned_data['key'],
                        value=cleaned_data['value'],
                        index=idx
                    )
                    rule.save()

            for idx, subform in enumerate(exclude_formset.forms):
                cleaned_data = subform.cleaned_data
                if cleaned_data:
                    rule = SegmentRule(
                        segment=self.object,
                        rule_type='exclude',
                        field=cleaned_data['field'],
                        conditional='AND' if idx == 0 else cleaned_data['conditional'],
                        key=None if cleaned_data['field'] not in ['has_attribute', 'clicked_url_in_instance'] else cleaned_data['key'],
                        value=cleaned_data['value'],
                        index=idx
                    )
                    rule.save()

            return response
        else:
            return super(SegmentCreateView, self).form_invalid(form)

    def get_success_url(self):
        return reverse('manager-segments-update', args=(self.object.id,))

class SegmentUpdateView(UpdateView):
    model = Segment
    form_class = SegmentForm
    template_name = 'manager/segments-update.html'

    def get_context_data(self, **kwargs):
        data = super(SegmentUpdateView, self).get_context_data(**kwargs)
        if self.request.POST:
            data['include_rules'] = IncludeSegmentRuleFormset(
                self.request.POST,
                instance=self.object,
                prefix='include_rules'
            )
            data['exclude_rules'] = ExcludeSegmentRuleFormset(
                self.request.POST,
                instance=self.object,
                prefix='exclude_rules'
            )
        else:
            data['include_rules'] = IncludeSegmentRuleFormset(
                instance=self.object,
                prefix='include_rules',
                queryset=self.object.include_rules.all()
            )
            data['exclude_rules'] = ExcludeSegmentRuleFormset(
                instance=self.object,
                prefix='exclude_rules',
                queryset=self.object.exclude_rules.all()
            )

        return data

    def form_valid(self, form):
        self.object = form.save(commit=False)
        context = self.get_context_data(form=form)
        include_formset = context['include_rules']
        exclude_formset = context['exclude_rules']

        if include_formset.is_valid() and exclude_formset.is_valid():
            self.object.include_rules.delete()
            self.object.exclude_rules.delete()

            for idx, subform in enumerate(include_formset.ordered_forms):
                cleaned_data = subform.cleaned_data
                if cleaned_data:
                    rule = SegmentRule(
                        segment=self.object,
                        rule_type='include',
                        field=cleaned_data['field'],
                        conditional='AND' if idx == 0 else cleaned_data['conditional'],
                        key=None if cleaned_data['field'] not in ['has_attribute', 'clicked_url_in_instance'] else cleaned_data['key'],
                        value=cleaned_data['value'],
                        index=idx
                    )
                    rule.save()

            for idx, subform in enumerate(exclude_formset.ordered_forms):
                cleaned_data = subform.cleaned_data
                if cleaned_data:
                    rule = SegmentRule(
                        segment=self.object,
                        rule_type='exclude',
                        field=cleaned_data['field'],
                        conditional='AND' if idx == 0 else cleaned_data['conditional'],
                        key=None if cleaned_data['field'] not in ['has_attribute', 'clicked_url_in_instance'] else cleaned_data['key'],
                        value=cleaned_data['value'],
                        index=idx
                    )
                    rule.save()

            form.save()
            response = super(SegmentUpdateView, self).form_valid(form)

            return response
        else:
            return super(SegmentUpdateView, self).form_invalid(form)

    def get_success_url(self):
        return reverse('manager-segments-update', args=(self.object.id,))

class SegmentDeleteView(DeleteView):
    model = Segment
    template_name = 'manager/segments-delete.html'

    def get_success_url(self):
        return reverse('manager-segments')

##
# Recipients
##
class RecipientListView(RecipientsMixin, SortSearchMixin, ListView):
    model = Recipient
    template_name = 'manager/recipients.html'
    context_object_name = 'recipients'
    paginate_by = 20

    def get_queryset(self):
        self.search_field = 'email_address'
        self.search_form = EmailSearchForm(self.request.GET)
        super(RecipientListView, self).get_queryset()

        self._search_form = RecipientSearchForm(self.request.GET)
        self._search_valid = self._search_form.is_valid()
        if self._search_valid:
            return Recipient.objects.filter(email_address__icontains=self._search_form.cleaned_data['search_query'])
        else:
            return Recipient.objects.all().order_by('disable', 'email_address')

    def get_context_data(self, **kwargs):
        context = super(RecipientListView, self).get_context_data(**kwargs)
        context['search_form'] = self._search_form
        context['search_valid'] = self._search_valid
        context['search_query'] = self._search_form.cleaned_data['search_query'] if self._search_valid else ''
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
            form._errors['name'] = ErrorList(['A attribute with that name already exists for this recipient.'])
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

    def get_context_data(self, **kwargs):
        context = super(RecipientSubscriptionsUpdateView, self).get_context_data()
        context['subscription_categories'] = SubscriptionCategory.objects.all()
        return context

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
        subscriptions = form.cleaned_data['subscription_categories']
        unsubscriptions = list(set(SubscriptionCategory.objects.all()) - set(subscriptions))

        for category in unsubscriptions:
            category.unsubscriptions.add(self.object)

        for category in subscriptions:
            category.unsubscriptions.remove(self.object)

        return super(RecipientSubscriptionsUpdateView, self).form_valid(form)

    def get_success_url(self):
        messages.success(self.request,
                         'Your subscriptions have been successfully updated.')
        return self.object.unsubscribe_url

class CampaignListView(ListView):
    model = Campaign
    template_name = 'manager/campaign-list.html'
    context_object_name = 'campaigns'

class CampaignCreateView(CreateView):
    model = Campaign
    template_name = 'manager/campaign-create.html'
    form_class = CampaignForm

    def form_valid(self, form):
        messages.success(self.request, 'Campaign successfully created.')
        return super(CampaignCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('manager-campaigns-update',
                      args=(),
                      kwargs={'pk': self.object.pk})

class CampaignUpdateView(UpdateView):
    model = Campaign
    template_name = 'manager/campaign-update.html'
    form_class = CampaignForm

    def form_valid(self, form):
        messages.success(self.request, 'Campaign successfully updated.')
        return super(CampaignUpdateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('manager-campaigns-update',
                      args=(),
                      kwargs={'pk': self.object.pk})

class CampaignDeleteView(DeleteView):
    model = Campaign
    template_name = 'manager/campaign-delete.html'
    context_object_name = 'campaign'

    def get_success_url(self):
        messages.success(self.request, 'Campaign successfully deleted.')
        return reverse('manager-campaigns',
                        args = (),
                        kwargs={})

class CampaignStatView(DetailView):
    model = Campaign
    template_name = 'manager/campaign-stats.html'
    context_object_name = 'campaign'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['instance_count'] = 0
        campaign = ctx.get('campaign', None)
        if campaign:
            for email in campaign.emails.all():
                ctx['instance_count'] += email.instances.count()

        return ctx

class SubscriptionCategoryListView(SubscriptionsMixin, ListView):
    model = SubscriptionCategory
    template_name = 'manager/subscription-category-list.html'
    context_object_name = 'categories'

class SubscriptionCategoryCreateView(SubscriptionsMixin, CreateView):
    model = SubscriptionCategory
    template_name = 'manager/subscription-category-create.html'
    form_class = SubscriptionCategoryForm

    def form_valid(self, form):
        messages.success(self.request, 'Subscription Category successfully created.')
        return super(SubscriptionCategoryCreateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('manager-subscription-categories-update',
                      args=(),
                      kwargs={'pk': self.object.pk})

class SubscriptionCategoryUpdateView(SubscriptionsMixin, UpdateView):
    model= SubscriptionCategory
    template_name = 'manager/subscription-category-update.html'
    form_class = SubscriptionCategoryForm

    def form_valid(self, form):
        messages.success(self.request, 'Subscription Category successfully updated.')
        return super(SubscriptionCategoryUpdateView, self).form_valid(form)

    def get_success_url(self):
        return reverse('manager-subscription-categories-update',
                      args=(),
                      kwargs={'pk': self.object.pk})

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
    template_name = 'manager/setting-delete-confirm.html'
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
    parser = HTMLParser()

    if not url_string or not position or not recipient_id or not mac or not instance_id:
        raise Http404("Poll does not exist")
    else:
        url_string = urllib.parse.unquote(url_string)
        url_part    = url_string.split('?')[0]

        if not URL.objects.filter(name__startswith=url_part).exists():
            raise Http404("Poll does not exist")
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
                            url_click, created = URLClick.objects.get_or_create(recipient=recipient, url=url)
                            log.debug('url click saved')
                    else:
                        log.error('wrong mac')
            else:
                log.error('something none')
        except Exception as e:
            log.error(str(e))
            pass
        # Decode any encoded characters to ensure things like
        # UTM params work appropriately

        url_string = parser.unescape(url_string)
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
                    log.error('multiple InstanceOpens returned');
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
            columns = list(col.strip() for col in form.cleaned_data['column_order'].split(','))
            column_order = ','.join(columns)
            skip_first_row = form.cleaned_data['skip_first_row']
            remove_stale = form.cleaned_data['remove_stale']
            csv_file = form.cleaned_data['csv_file']
            existing_group_id = None

            group = ""
            if existing_group_name is not None:
                group = existing_group_name
                existing_group_id = form.cleaned_data['existing_group_name'].pk
            else:
                group = new_group_name

            filename = settings.UPLOAD_DIR + "/" +  csv_file.name

            with open(filename, 'wb+') as dest:
                for chunk in csv_file.chunks():
                    dest.write(chunk)

            if (existing_group_id):
                success_url = reverse('manager-recipientgroup-update', kwargs={'pk': existing_group_id})
            else:
                success_url = None

            tracker = SubprocessStatus.objects.create(
                name="Importing {0} into \"{1}\"...".format(csv_file.name, group),
                current_unit=1,
                total_units=1,
                unit_name='recipients',
                success_url=success_url,
                back_url=reverse('manager-recipients-csv-import')
            )

            self.tracker_pk = tracker.pk

            command = [
                sys.executable,
                'manage.py',
                'import-emails',
                filename,
                '--group-name={0}'.format(group),
                '--column-order={0}'.format(column_order),
                '--subprocess={0}'.format(self.tracker_pk)
            ]

            if skip_first_row:
                command.append('--ignore-first-row')

            if remove_stale:
                command.append('--remove-stale')

            subprocess.Popen(
                command,
                close_fds=True,
                cwd=settings.BASE_DIR
            )

            # messages.success(self.request, 'Emails successfully imported.')
            return super(RecipientCSVImportView, self).form_valid(form)

    def get_success_url(self):
        return reverse('subprocess-status-detail-view', kwargs={ 'pk': self.tracker_pk })


class ExportCleanupView(FormView):
    template_name = 'manager/export-cleanup.html'
    form_class = ExportCleanupForm

    def get_context_data(self, **kwargs):
        context = super(ExportCleanupView, self).get_context_data(**kwargs)

        removal_hash = self.request.GET.get('hash', None)
        context['hash'] = removal_hash

        if removal_hash:
            try:
                stale = StaleRecord.objects.get(removal_hash=removal_hash)
                earliest = stale.instances.aggregate(Min('end'))
                latest = stale.instances.aggregate(Max('end'))
                context['stale'] = stale
                context['earliest'] = earliest['end__min'] if 'end__min' in earliest else None
                context['latest'] = latest['end__max'] if 'end__max' in latest else None
            except StaleRecord.DoesNotExist:
                context['stale'] = None

        return context

    def form_valid(self, form):
        if form.is_valid:
            removal_hash = self.request.GET.get('hash')

            if 'remove_emails' in form.cleaned_data:
                remove_emails = form.cleaned_data['remove_emails']
            else:
                remove_emails = False


            success_url = reverse('manager-home')
            back_url = reverse('manager-export-cleanup')

            self.tracker = SubprocessStatus.objects.create(
                name="Deleting stale records...",
                current_unit=1,
                total_units=1,
                unit_name='records',
                success_url=success_url,
                back_url=back_url
            )

            command = [
                sys.executable,
                'manage.py',
                'remove-stale',
                removal_hash,
                '--quiet=True',
                '--subprocess={0}'.format(self.tracker.pk)
            ]

            if remove_emails:
                command.append('--remove-empty-emails=True')

            subprocess.Popen(
                command,
                close_fds=True,
                cwd=settings.BASE_DIR
            )

            return super(ExportCleanupView, self).form_valid(form)

    def get_success_url(self):
        return reverse('subprocess-status-detail-view', kwargs={ 'pk': self.tracker.pk })

class SubprocessStatusDetailView(DetailView):
    model = SubprocessStatus
    template_name = 'manager/subprocess-status.html'

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

def subprocess_status_json_feed(request):
    retval = {}

    if request.GET.get('pk'):
        pk = request.GET.get('pk')

        try:
            sp = SubprocessStatus.objects.get(pk=pk)

            retval['current_unit'] = sp.current_unit
            retval['total_units'] = sp.total_units
            retval['unit_name'] = sp.unit_name
            retval['status'] = sp.status
            retval['error'] = sp.error
            retval['success_url'] = sp.success_url
            retval['back_url'] = sp.back_url
        except SubprocessStatus.DoesNotExist:
            retval['error'] = 'Error getting Subprocess Status'
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


def objects_as_options(request):
    """
    Provides a simple API endpoint for retrieving
    various postmaster objects as options for a
    select2 control.
    """
    object_type = request.GET.get('type', None)
    query = request.GET.get('q', None)

    retval = {}
    ret_status = 200

    if object_type:
        results = []

        if object_type == 'recipientgroup':
            objects = RecipientGroup.objects.all()
            if query:
                objects = objects.filter(name__contains=query)
            results = [{'text': x.name, 'id': x.id} for x in objects]
        elif object_type == 'recipientattribute':
            objects = RecipientAttribute.objects.values_list('name').distinct()
            results = [{'text': x[0], 'id': x[0]} for x in objects]
        elif object_type == 'instance':
            objects = Instance.objects.all()
            if query:
                objects = objects.filter(
                    Q(email__title__icontains=query) |
                    Q(subject__icontains=query)
                )
            results = [{'text': x.option_text, 'id': x.id} for x in objects]
        elif object_type == 'email':
            objects = Email.objects.all()
            if query:
                objects = objects.filter(title__icontains=query)
            results = [{'text': x.title, 'id': x.id} for x in objects]
        elif object_type == 'url':
            objects = URL.objects.all()
            if query:
                objects = objects.filter(name__iconatins=query)
            results = [{'text': x.name, 'id': x.id} for x in objects]

        retval['results'] = results
    else:
        ret_status = 400
        retval = {
            'error': 'You must specify an object type to query for by passing a "type" parameter.'
        }

    return HttpResponse(json.dumps(retval), content_type='application/json', status=ret_status)

##
# Creates a recipient group based on email opens.
# POST only
##
def create_recipient_group_action(request):
    action = request.POST.get('group-create-action')

    email_instance_id = request.POST.get('email-instance-id')
    email_instance = Instance.objects.get(pk=email_instance_id)

    if (action == 'opens'):
        return create_recipient_group_email_opens(request, email_instance)
    elif (action == 'unopens'):
        return create_recipient_group_email_unopens(request, email_instance)
    elif (action == 'no-clicks'):
        return create_recipient_group_no_clicks(request, email_instance)
    else:
        return HttpResponse(
            '<h1>Invalid Action</h1>',
            status=400
        )

def create_recipient_group_email_opens(request, email_instance):
    '''
    Creates a recipient group based on email opens.
    POST only
    '''
    recipients = email_instance.open_recipients

    recipient_group = RecipientGroup(name=email_instance.email.title + ' Recipient Group ' + datetime.now().strftime('%m-%d-%y %I:%M %p'))
    if RecipientGroup.objects.filter(name=recipient_group.name).count() > 0:
        recipient_group.name = recipient_group.name + '-1'

    recipient_group.save()

    recipient_group.recipients.add(*recipients)

    recipient_group.save()

    messages.success(request, 'Recipient group successfully created. Please remember to update the name to something unique.')
    return HttpResponseRedirect(
        reverse('manager-recipientgroup-update',
            args=(),
            kwargs={'pk': recipient_group.pk}
        )
    )

def create_recipient_group_email_unopens(request, email_instance):
    '''
    Creates a recipient group based on emails
    that did not open the email
    POST only
    '''
    recipients_pks = InstanceOpen.objects.filter(instance=email_instance).values_list('recipient__pk', flat=True)

    # Remove all the opens from the sent recipients
    recipients = email_instance.recipients.exclude(pk__in=recipients_pks)

    recipient_group = RecipientGroup(name=email_instance.email.title + ' Recipient Group - Unopens - ' + datetime.now().strftime('%m-%d-%y %I:%M %p'))
    if RecipientGroup.objects.filter(name=recipient_group.name).count() > 0:
        recipient_group.name = recipient_group.name + '-1'

    recipient_group.save()

    recipient_group.recipients.add(*recipients)

    recipient_group.save()

    messages.success(request, 'Recipient group successfully created. Please remember to update the name to something unique.')
    return HttpResponseRedirect(
        reverse('manager-recipientgroup-update',
            args=(),
            kwargs={'pk': recipient_group.pk}
        )
    )

def create_recipient_group_no_clicks(request, email_instance):
    '''
    Creates a recipient group with recipients
    who did not click on any links for a
    particular email instance.
    '''
    recipients = email_instance.recipients.all()

    recipient_clicks = URLClick.objects.filter(url__in=email_instance.urls.all()).values('recipient__id').distinct()
    recipient_clicks = Recipient.objects.filter(id__in=recipient_clicks)

    recipients = list(set(recipients) - set(recipient_clicks))

    recipient_group = RecipientGroup(name=email_instance.email.title + ' Recipient Group - No Clicks - ' + datetime.now().strftime('%m-%d-%y %I:%M %p'))
    if RecipientGroup.objects.filter(name=recipient_group.name).count() > 0:
        recipient_group.name = recipient_group.name + '-1'

    recipient_group.save()

    recipient_group.recipients.add(*recipients)

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

    recipients = []

    for url_click in url_clicks:
        for click in url_click:
            recipients.append(click.recipient)

    recipient_group.recipients.add(*recipients)

    recipient_group.save()

    messages.success(request, 'Recipient group successfully created. Please remember to update the name to something unique.')
    return HttpResponseRedirect(
        reverse('manager-recipientgroup-update',
            args=(),
            kwargs={'pk': recipient_group.pk}
        )
    )

def csv_export_recipient_group(request, pk):
    try:
        group = RecipientGroup.objects.get(pk=pk)
    except RecipientGroup.DoesNotExist:
        return HttpResponse(
            '<h1>The recipient group does not exist.</h1>',
            status=400
        )

    filename = "{0}-export.csv".format(group.name)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="{0}"'.format(filename)

    writer = csv.writer(response)

    writer.writerow(['email'])

    for recipient in group.recipients.all():
        writer.writerow([recipient.email_address])

    return response

def stale_record_action(request):
    removal_hash = request.GET.get('hash')

    try:
        record = StaleRecord.objects.get(removal_hash=removal_hash)
    except StaleRecord.DoesNotExist:
        return HttpResponse(
            '<h1>The recipient group does not exist.</h1>',
            status=400
        )

    command = [
        sys.executable,
        'manage.py',
        'remove-stale',
        record.removal_hash,
        '--remove-empty-emails=True',
        '--quiet=True'
    ]

    subprocess.Popen(
        command,
        close_fds=True,
        cwd=settings.BASE_DIR
    )

    messages.success(request, 'Records removed.')

    return HttpResponseRedirect(
        reverse('manager-home',
            args=()
        )
    )


def s3_upload_user_file(request):
    """
    Uploads a unique file to Amazon S3, using a key prefixed with the current
    year + month.

    Returns json containing uploaded file url ( {link: '...'} ) or error
    message ( {error: '...'} ).
    """
    today = datetime.today()
    if request.method == 'POST':
        response_data = {}
        file = request.FILES['file']
        file_prefix = str(today.year) + '/' + '{:02d}'.format(today.month) + '/'
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
            except AmazonS3Helper.KeyCreateError as e:
                response_data['error'] = 'Failed to upload file.'
            except PermissionDenied:
                response_data['error'] = 'Cannot upload this type of file.'

            try:
                url = keyobj.generate_url(0, query_auth=False, force_http=True)
            except Exception as e:
                response_data['error'] = 'Failed to generate url for file.'

            if url:
                if protocol != 'http://':
                    url = url.replace('http://', protocol)
                response_data['link'] = url

        return HttpResponse(
            json.dumps(response_data),
            content_type='application/json'
        )
    else:
        return HttpResponseForbidden()
