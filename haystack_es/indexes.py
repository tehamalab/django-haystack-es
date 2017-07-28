# -*- coding: utf-8


from __future__ import absolute_import, division, print_function, unicode_literals

import threading

from django.utils.six import with_metaclass

from haystack.manager import SearchIndexManager
from haystack.indexes import *  # noqa: F403

from .fields import *  # noqa: F403


class Elasticsears5DeclarativeMetaclass(DeclarativeMetaclass):  # noqa: F405

    def __new__(cls, name, bases, attrs):
        attrs['fields'] = {}

        # Inherit any fields from parent(s).
        try:
            parents = [b for b in bases if issubclass(b, SearchIndex)]
            # Simulate the MRO.
            parents.reverse()

            for p in parents:
                fields = getattr(p, 'fields', None)

                if fields:
                    attrs['fields'].update(fields)
        except NameError:
            pass

        # Build a dictionary of faceted fields for cross-referencing.
        facet_fields = {}

        for field_name, obj in attrs.items():
            # Only need to check the FacetFields.
            if hasattr(obj, 'facet_for'):
                if obj.facet_for not in facet_fields:
                    facet_fields[obj.facet_for] = []

                facet_fields[obj.facet_for].append(field_name)

        built_fields = {}

        for field_name, obj in attrs.items():
            if isinstance(obj, SearchField):  # noqa: F405
                field = attrs[field_name]
                field.set_instance_name(field_name)
                built_fields[field_name] = field

        attrs['fields'].update(built_fields)

        # Assigning default 'objects' query manager if it does not already exist
        if 'objects' not in attrs:
            try:
                attrs['objects'] = SearchIndexManager(attrs['Meta'].index_label)
            except (KeyError, AttributeError):
                attrs['objects'] = SearchIndexManager(DEFAULT_ALIAS)  # noqa: F405

        return type.__new__(cls, name, bases, attrs)


DeclarativeMetaclass = Elasticsears5DeclarativeMetaclass


class _Elasticsearch5Index(with_metaclass(DeclarativeMetaclass, threading.local)):
    pass


class Elasticsearch5SearchIndex(SearchIndex, _Elasticsearch5Index):  # noqa: F405
    pass


SearchIndex = Elasticsearch5SearchIndex


class BasicSearchIndex(SearchIndex):
    text = CharField(document=True, use_template=True)  # noqa: F405


class Elasticsearch5ModelSearchIndex(ModelSearchIndex, SearchIndex):  # noqa: F405
    pass


ModelSearchIndex = Elasticsearch5ModelSearchIndex


try:
    from celery_haystack.indexes import CelerySearchIndex

    class Elasticsearch5CelerySearchIndex(CelerySearchIndex, SearchIndex):
        pass

    CelerySearchIndex = Elasticsearch5CelerySearchIndex
except ImportError:
    pass
