# -*- coding: utf-8
from __future__ import unicode_literals, absolute_import

from django.conf.urls import url, include

from haystack_es.urls import urlpatterns as haystack_es_urls

urlpatterns = [
    url(r'^', include(haystack_es_urls, namespace='haystack_es')),
]
