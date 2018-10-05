from django.conf.urls               import include, url
from manager.views                  import *
from django.views.generic           import TemplateView
from django.contrib.auth.decorators import login_required

urlpatterns = [
    # Emails
    url(r'^email/unsubscribe/?$',                   RecipientSubscriptionsUpdateView.as_view(),                 name='manager-email-unsubscribe-old'),
    url(r'^email/open/?$',                          instance_open,                                              name='manager-email-open'),
    url(r'^email/redirect/?$',                      redirect,                                                   name='manager-email-redirect'),
    url(r'^email/create/$',                         login_required(EmailCreateView.as_view()),                  name='manager-email-create'),
    url(r'^email/(?P<pk>\d+)/delete/$',             login_required(EmailDeleteView.as_view()),                  name='manager-email-delete'),
    url(r'^email/(?P<pk>\d+)/update/$',             login_required(EmailUpdateView.as_view()),                  name='manager-email-update'),
    url(r'^email/(?P<pk>\d+)/verify-placeholders/$', login_required(EmailPlaceholderVerificationView.as_view()), name='manager-email-placeholder-verification'),
    url(r'^email/(?P<pk>\d+)/previewinstances/$',   login_required(PreviewInstanceListView.as_view()),          name='manager-email-preview-instances'),
    url(r'^email/(?P<pk>\d+)/previewinstances/lockcontent/$', login_required(LockContentView.as_view()),        name='manager-email-lock-content'),
    url(r'^email/(?P<pk>\d+)/instances/$',          login_required(InstanceListView.as_view()),                 name='manager-email-instances'),
    url(r'^email/(?P<pk>\d+)/unsubscriptions/$',    login_required(EmailUnsubscriptionsListView.as_view()),     name='manager-email-unsubscriptions'),
    url(r'^email/instant-send/$',                   login_required(EmailInstantSendView.as_view()),             name='manager-email-instant-send'),
    url(r'^email/instance/(?P<pk>\d+)/$',           login_required(InstanceDetailView.as_view()),               name='manager-email-instance'),
    url(r'^email/instance/(?P<pk>\d+)/saved/$',     login_required(InstanceDetailView.as_view(template_name='manager/email-instance-saved.html')), name='manager-email-instance-saved'),
    url(r'^email/instance/(?P<pk>\d+)/cancel/$',    login_required(instance_cancel),                                     name='manager-instance-cancel'),
    url(r'^instance/json/$',                        login_required(instance_json_feed),                         name='manager-instance-json'),
    url(r'^emails/$',                               login_required(EmailListView.as_view()),                    name='manager-emails'),

    # Recipients
    url(r'^recipientgroups/$',                        login_required(RecipientGroupLiveListView.as_view()),      name='manager-recipientgroups'),
    url(r'^recipientgroups/preview-groups/$',         login_required(RecipientGroupPreviewListView.as_view()),   name='manager-recipientgroups-previewgroups'),
    url(r'^recipientgroup/create/$',                  login_required(RecipientGroupCreateView.as_view()),        name='manager-recipientgroup-create'),
    url(r'^recipientgroup/create/email-opens/$',      login_required(create_recipient_group_email_opens),        name='manager-recipientgroup-create-email-opens'),
    url(r'^recipientgroup/create/url-clicks/$',       login_required(create_recipient_group_url_clicks),         name='manager-recipientgroup-create-url-clicks'),
    url(r'^recipientgroup/(?P<pk>\d+)/update/$',      login_required(RecipientGroupUpdateView.as_view()),        name='manager-recipientgroup-update'),
    url(r'^recipientgroup/(?P<pk>\d+)/delete/$',      login_required(RecipientGroupDeleteView.as_view()),        name='manager-recipientgroup-delete'),
    url(r'^recipients/$',                             login_required(RecipientListView.as_view()),               name='manager-recipients'),
    url(r'^recipients/json/$',                        login_required(recipient_json_feed),                       name='manager-recipients-json'),
    url(r'^recipients/csv-import/$',                  login_required(RecipientCSVImportView.as_view()),          name='manager-recipients-csv-import'),
    url(r'^recipient/create/$',                       login_required(RecipientCreateView.as_view()),             name='manager-recipient-create'),
    url(r'^recipient/attribute/(?P<pk>\d+)/delete/$', login_required(RecipientAttributeDeleteView.as_view()),    name='manager-recipientattribute-delete'),
    url(r'^recipient/attribute/(?P<pk>\d+)/update/$', login_required(RecipientAttributeUpdateView.as_view()),    name='manager-recipientattribute-update'),
    url(r'^recipient/(?P<pk>\d+)/attribute/create/$', login_required(RecipientAttributeCreateView.as_view()),    name='manager-recipientattribute-create'),
    url(r'^recipient/(?P<pk>\d+)/attributes/$',       login_required(RecipientAttributeListView.as_view()),      name='manager-recipient-recipientattributes'),
    url(r'^recipient/(?P<pk>\d+)/update/$',           login_required(RecipientUpdateView.as_view()),             name='manager-recipient-update'),
    url(r'^recipient/(?P<pk>\d+)/subscriptions/$',    RecipientSubscriptionsUpdateView.as_view(),                name='manager-recipient-subscriptions'),

    # Reports
    url(r'^reporting/$', login_required(ReportView.as_view()), name='manager-report-view'),

    # Settings
    url(r'^setting/create/$',                      login_required(SettingCreateView.as_view()),      name='manager-setting-create'),
    url(r'^setting/(?P<pk>\d+)/delete/$',          login_required(SettingDeleteView.as_view()),      name='manager-setting-delete'),
    url(r'^setting/(?P<pk>\d+)/update/$',          login_required(SettingUpdateView.as_view()),      name='manager-setting-update'),
    url(r'^settings/$',                            login_required(SettingListView.as_view()),        name='manager-settings'),

    # Subscriptions
    url(r'^subscriptions/categories/$',                    login_required(SubscriptionCategoryListView.as_view()),   name='manager-subscription-categories'),
    url(r'^subscriptions/categories/create/$',             login_required(SubscriptionCategoryCreateView.as_view()), name='manager-subscription-categories-create'),
    url(r'^subscriptions/categories/(?P<pk>\d+)/update/$', login_required(SubscriptionCategoryUpdateView.as_view()), name='manager-subscription-categories-update'),

    url(r'^subprocess/status/(?P<pk>\d+)/$',   login_required(SubprocessStatusDetailView.as_view()), name='subprocess-status-detail-view'),
    url(r'^subprocess/json/$',                 login_required(subprocess_status_json_feed),          name='subprocess-status-json'),

    # S3 User File Handling
    url(r'^files/upload/$', login_required(s3_upload_user_file), name='manager-file-upload'),

    url(r'^$', login_required(OverviewListView.as_view()), name='manager-home'),
]
