from django.conf.urls import url

from sns.views import Endpoint

urlpatterns = [
    url(r'^$', Endpoint.as_view(), name='sns-endpoint')
]
