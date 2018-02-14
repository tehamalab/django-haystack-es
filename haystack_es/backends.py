# -*- coding: utf-8

import warnings
import ast
from datetime import datetime, timedelta

import elasticsearch

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

import haystack
from haystack.backends.elasticsearch_backend import ElasticsearchSearchBackend, ElasticsearchSearchQuery
from haystack.backends import SearchNode, BaseEngine, log_query
from haystack.models import SearchResult
from haystack.constants import (DEFAULT_OPERATOR, DJANGO_CT, DJANGO_ID, FUZZY_MAX_EXPANSIONS, DEFAULT_ALIAS,
                                FILTER_SEPARATOR, VALID_FILTERS)
from haystack.utils import get_model_ct
from haystack.utils.app_loading import haystack_get_model

__all__ = ['Elasticsearch5SearchBackend', 'Elasticsearch5SearchEngine']

DATE_HISTOGRAM_FIELD_NAME_SUFFIX = '_haystack_date_histogram'
DATE_RANGE_FIELD_NAME_SUFFIX = '_haystack_date_range'

DEFAULT_FIELD_MAPPING = {'type': 'text', 'analyzer': 'snowball', 'fielddata': True}
FIELD_MAPPINGS = {
    'edge_ngram': {'type': 'text', 'analyzer': 'edgengram_analyzer'},
    'ngram': {'type': 'text', 'analyzer': 'ngram_analyzer'},
    'date': {'type': 'date'},
    'datetime': {'type': 'date'},
    'boolean': {'type': 'boolean'},
    'float': {'type': 'float'},
    'long': {'type': 'long'},
    'integer': {'type': 'long'},
    'dict': {'type': 'object'},
    'nested': {'type': 'nested'},
    'location': {'type': 'geo_point'},
    'geometry': {'type': 'geo_shape'},
}

NESTED_FILTER_SEPARATOR = '>'


class Elasticsearch5SearchBackend(ElasticsearchSearchBackend):

    def build_schema(self, fields):
        content_field_name = ''
        mapping = {
            DJANGO_CT: {'type': 'text', 'index': 'not_analyzed', 'include_in_all': False},
            DJANGO_ID: {'type': 'text', 'index': 'not_analyzed', 'include_in_all': False},
        }

        for field_name, field_class in fields.items():
            field_mapping = FIELD_MAPPINGS.get(field_class.field_type, DEFAULT_FIELD_MAPPING).copy()

            if field_class.document is True:
                content_field_name = field_class.index_fieldname

            if field_mapping['type'] == 'text':
                if field_class.indexed is False or hasattr(field_class, 'facet_for'):
                    # do not analyze
                    field_mapping['index'] = 'not_analyzed'
                    field_mapping['type'] = 'keyword'

            if field_mapping['type'] not in ['object', 'nested', 'geo_point', 'geo_shape']:
                # add raw field
                if not field_mapping.get('fields'):
                    field_mapping['fields'] = {}
                if field_mapping['type'] == 'text':
                    field_mapping['fields']['raw'] = {'type': 'keyword'}
                else:
                    field_mapping['fields']['raw'] = {
                        'type': field_mapping['type']}

            mapping[field_class.index_fieldname] = field_mapping

        return (content_field_name, mapping)

    def build_search_kwargs(self, query_string, sort_by=None, start_offset=0, end_offset=None,
                            fields='', highlight=False, boost_fields=None, boost_negative=None,
                            filter_context=None, narrow_queries=None, spelling_query=None,
                            facets=None, date_facets=None, query_facets=None,
                            within=None, dwithin=None, distance_point=None,
                            models=None, limit_to_registered_models=None, result_class=None,
                            **extra_kwargs):

        index = haystack.connections[self.connection_alias].get_unified_index()
        content_field = index.document_field

        filters = []
        filters_with_score = []
        filter_query_strings = {
            'content': u'%s',
            'contains': u'*%s*',
            'endswith': u'*%s',
            'startswith': u'%s*',
            'exact': u'%s',
            'gt': u'{%s TO *}',
            'gte': u'[%s TO *]',
            'lt': u'{* TO %s}',
            'lte': u'[* TO %s]',
            'fuzzy': u'%s~',
        }

        if filter_context:
            for f in filter_context:
                if f.get('content'):
                    content = str(f.pop('content'))
                    if query_string == '*:*':
                        query_string = content
                    else:
                        query_string = '%s %s' % (query_string, content)
                for k, v in f.items():
                    _filter = None
                    _filter_with_score = None
                    try:
                        _value = v.prepare()
                    except AttributeError:
                        _value = str(v)
                    _field, _lookup = self.get_filter_lookup(k)
                    _is_nested = NESTED_FILTER_SEPARATOR in _field
                    _nested_path = None
                    if _is_nested:
                        _nested_path = _field.split(NESTED_FILTER_SEPARATOR)[0]
                        _field = ('.').join(_field.split(NESTED_FILTER_SEPARATOR))
                    if _lookup == 'exact':
                        if _is_nested:
                            _filter = {'term': {_field: _value}}
                        else:
                            _filter = {'term': {_field + '.raw': _value}}
                    elif _lookup == 'content':
                        _filter_with_score = {'match': {_field: _value}}
                    elif _lookup == 'in':
                        if not isinstance(_value, list):
                            _value = ast.literal_eval(str(_value))
                        _filter = {
                            'query_string': {
                                'fields': [_field],
                                'query': ' OR '.join(['"%s"' % i for i in _value])
                            }}
                    elif _lookup == 'range':
                        if isinstance(_value, dict):
                            _filter = {'range': {_field: _value}}
                        elif _value:
                            if not isinstance(_value, list):
                                _value = _value.split(',')
                            if len(_value) >= 2:
                                _range = {}
                                _range['gte'] = _value[0]
                                _range['lte'] = _value[1]
                                _filter = {'range': {_field: _range}}
                            else:
                                raise ValueError(
                                    _('Range lookup requires minimum and maximum values,'
                                      'only one value was provided'))
                    else:
                        _filter = {
                            'query_string': {
                                'fields': [_field],
                                'query': filter_query_strings[_lookup] % _value,
                            }}

                    # nested filter
                    if _is_nested:
                        if _filter:
                            _filter = {
                                'nested': {
                                    'path': _nested_path,
                                    'query': _filter
                                }
                            }
                        if _filter_with_score:
                            _filter_with_score = {
                                'nested': {
                                    'path': _nested_path,
                                    'query': _filter_with_score
                                }
                            }

                    if _filter:
                        filters.append(_filter)
                    if _filter_with_score:
                        filters.append(_filter_with_score)

        if query_string == '*:*':
            kwargs = {
                'query': {
                    "match_all": {}
                },
            }
        else:
            kwargs = {
                'query': {
                    'query_string': {
                        'fields': [content_field],
                        'default_operator': DEFAULT_OPERATOR,
                        'query': query_string,
                        'analyze_wildcard': True,
                        'auto_generate_phrase_queries': True,
                        'fuzzy_max_expansions': FUZZY_MAX_EXPANSIONS,
                    },
                },
            }
            if boost_fields:
                kwargs['query']['query_string']['fields'] = []
                for boost_field, boost_value in boost_fields.items():
                    kwargs['query']['query_string']['fields'].append('%s^%s' % (boost_field, boost_value))
            if boost_negative:
                boosting = {
                    'positive': kwargs['query'],
                    'negative': boost_negative[0],
                    'negative_boost': boost_negative[1]
                }
                kwargs['query'] = {'boosting': boosting}

        if filters_with_score:
            kwargs['query'] = {"bool": {"must": [kwargs.pop("query")]}}
            kwargs['query']['bool']['must'] += filters_with_score

        if fields:
            if isinstance(fields, (list, set)):
                fields = " ".join(fields)

            kwargs['stored_fields'] = fields

        if sort_by is not None:
            order_list = []
            for field, direction in sort_by:
                if field == 'distance' and distance_point:
                    lng, lat = distance_point['point'].get_coords()
                    sort_kwargs = {
                        "_geo_distance": {
                            distance_point['field']: [lng, lat],
                            "order": direction,
                            "unit": "km"
                        }
                    }
                else:
                    if field == 'distance':
                        warnings.warn(
                            "In order to sort by distance, "
                            "you must call the '.distance(...)' method.")

                    sort_kwargs = {field: {'order': direction}}

                order_list.append(sort_kwargs)

            kwargs['sort'] = order_list

        if highlight:
            kwargs['highlight'] = {
                'fields': {
                    content_field: {},
                }
            }

            if isinstance(highlight, dict):
                kwargs['highlight'].update(highlight)

        if self.include_spelling:
            kwargs['suggest'] = {
                'suggest': {
                    'text': spelling_query or query_string,
                    'term': {
                        'field': '_all',
                    },
                },
            }

        if narrow_queries is None:
            narrow_queries = set()

        if facets is not None:
            kwargs.setdefault('aggregations', {})

            for facet_fieldname, extra_options in facets.items():
                facet_options = {
                    'terms': {
                        'field': facet_fieldname + '.raw',
                        'size': 100,
                    },
                }
                # Special cases for options applied at the facet level (not the terms level).
                if extra_options.pop('global_scope', False):
                    # Renamed "global_scope" since "global" is a python keyword.
                    facet_options['global'] = True
                if 'facet_filter' in extra_options:
                    facet_options['facet_filter'] = extra_options.pop('facet_filter')
                facet_options['terms'].update(extra_options)
                kwargs['aggregations'][facet_fieldname] = facet_options

        if date_facets is not None:
            kwargs.setdefault('aggregations', {})

            for facet_fieldname, value in date_facets.items():
                # Need to detect on gap_by & only add amount if it's more than one.
                interval = value.get('gap_by').lower()

                # Need to detect on amount (can't be applied on months or years).
                if value.get('gap_amount', 1) != 1 and interval not in ('month', 'year'):
                    # Just the first character is valid for use.
                    interval = "%s%s" % (value['gap_amount'], interval[:1])

                date_histogram_aggregation_name = "{0}{1}".format(facet_fieldname,
                                                                  DATE_HISTOGRAM_FIELD_NAME_SUFFIX)
                date_range_aggregation_name = "{0}{1}".format(facet_fieldname, DATE_RANGE_FIELD_NAME_SUFFIX)

                kwargs['aggregations'][date_histogram_aggregation_name] = {
                    'meta': {
                        '_type': 'haystack_date_histogram',
                    },
                    'date_histogram': {
                        'field': facet_fieldname,
                        'interval': interval,
                    },
                }

                kwargs['aggregations'][date_range_aggregation_name] = {
                    'meta': {
                        '_type': 'haystack_date_range',
                    },
                    'date_range': {  # agg type
                        'field': facet_fieldname,
                        'ranges': [
                            {
                                'from': self._from_python(value.get('start_date')),
                                'to': self._from_python(value.get('end_date')),
                            }
                        ]
                    }
                }

        if query_facets is not None:
            kwargs.setdefault('aggregations', {})

            for facet_fieldname, value in query_facets:
                kwargs['aggregations'][facet_fieldname] = {
                    'filter': {
                        'query_string': {
                            'query': value,
                        }
                    }
                }

        if limit_to_registered_models is None:
            limit_to_registered_models = getattr(settings, 'HAYSTACK_LIMIT_TO_REGISTERED_MODELS', True)

        if models and len(models):
            model_choices = sorted(get_model_ct(model) for model in models)
        elif limit_to_registered_models:
            # Using narrow queries, limit the results to only models handled
            # with the current routers.
            model_choices = self.build_models_list()
        else:
            model_choices = []

        if len(model_choices) > 0:
            filters.append({"terms": {DJANGO_CT: model_choices}})

        for q in narrow_queries:
            filters.append(
                {
                    'query_string': {'query': q}
                }
            )

        if within is not None:
            from haystack.utils.geo import generate_bounding_box

            ((south, west), (north, east)) = generate_bounding_box(within['point_1'], within['point_2'])
            within_filter = {
                "geo_bounding_box": {
                    within['field']: {
                        "top_left": {
                            "lat": north,
                            "lon": west
                        },
                        "bottom_right": {
                            "lat": south,
                            "lon": east
                        }
                    }
                },
            }
            filters.append(within_filter)

        if dwithin is not None:
            lng, lat = dwithin['point'].get_coords()

            # NB: the 1.0.0 release of elasticsearch introduce an
            #     incompatible change on the distance filter formating
            if elasticsearch.VERSION >= (1, 0, 0):
                distance = "%(dist).6f%(unit)s" % {
                    'dist': dwithin['distance'].km,
                    'unit': "km"
                }
            else:
                distance = dwithin['distance'].km

            dwithin_filter = {
                "geo_distance": {
                    "distance": distance,
                    dwithin['field']: {
                        "lat": lat,
                        "lon": lng
                    }
                }
            }
            filters.append(dwithin_filter)

        # if we want to filter, change the query type to filteres
        if filters:
            kwargs["query"] = {"bool": {"must": kwargs.pop("query")}}

            if len(filters) == 1:
                kwargs['query']['bool']["filter"] = filters[0]
            else:
                kwargs['query']['bool']["filter"] = {"bool": {"must": filters}}

        if extra_kwargs:
            kwargs.update(extra_kwargs)
        return kwargs

    @log_query
    def search(self, query_string, **kwargs):

        if len(query_string) == 0:
            return {
                'results': [],
                'hits': 0,
            }

        if not self.setup_complete:
            self.setup()

        search_kwargs = self.build_search_kwargs(query_string, **kwargs)
        search_kwargs['from'] = kwargs.get('start_offset', 0)

        order_fields = set()

        for order in search_kwargs.get('sort', []):
            for key in order.keys():
                order_fields.add(key)

        geo_sort = '_geo_distance' in order_fields

        end_offset = kwargs.get('end_offset')
        start_offset = kwargs.get('start_offset', 0)

        if end_offset is not None and end_offset > start_offset:
            search_kwargs['size'] = end_offset - start_offset

        try:
            raw_results = self.conn.search(body=search_kwargs, index=self.index_name, doc_type='modelresult',
                                           _source=True)
        except elasticsearch.TransportError as e:
            if not self.silently_fail:
                raise

            self.log.error("Failed to query Elasticsearch using '%s': %s", query_string, e, exc_info=True)
            raw_results = {}

        return self._process_results(raw_results,
                                     highlight=kwargs.get('highlight'),
                                     result_class=kwargs.get('result_class', SearchResult),
                                     distance_point=kwargs.get('distance_point'),
                                     geo_sort=geo_sort)

    def _process_results(self, raw_results, highlight=False, result_class=None,
                         distance_point=None, geo_sort=False):
        from haystack import connections
        results = []
        hits = raw_results.get('hits', {}).get('total', 0)
        facets = {}
        spelling_suggestion = None

        if result_class is None:
            result_class = SearchResult

        if self.include_spelling and 'suggest' in raw_results:
            raw_suggest = raw_results['suggest'].get('suggest')
            if raw_suggest:
                spelling_suggestion = ' '.join(
                    [
                        word['text'] if len(word['options']) == 0 else word['options'][0]['text']
                        for word in raw_suggest
                    ]
                )

        if 'aggregations' in raw_results:
            facets = {
                'fields': {},
                'dates': {},
                'queries': {},
            }

            # ES can return negative timestamps for pre-1970 data. Handle it.
            def from_timestamp(tm):
                if tm >= 0:
                    return datetime.utcfromtimestamp(tm)
                else:
                    return datetime(1970, 1, 1) + timedelta(seconds=tm)

            for facet_fieldname, facet_info in raw_results['aggregations'].items():

                try:
                    facet_type = facet_info['meta']['_type']
                except KeyError:
                    facet_type = 'terms'

                if facet_type == 'terms':
                    facets['fields'][facet_fieldname] = [
                        (bucket['key'], bucket['doc_count']) for bucket in facet_info.get('buckets', [])
                    ]

                elif facet_type == 'haystack_date_histogram':
                    # Elasticsearch provides UTC timestamps with an extra three
                    # decimals of precision, which datetime barfs on.
                    dates = [
                        (from_timestamp(bucket['key'] / 1000), bucket['doc_count'])
                        for bucket in facet_info.get('buckets', [])
                    ]
                    facets['dates'][facet_fieldname[:-len(DATE_HISTOGRAM_FIELD_NAME_SUFFIX)]] = dates

                elif facet_type == 'haystack_date_range':
                    pass

                elif facet_type == 'query':
                    facets['queries'][facet_fieldname] = facet_info['count']

        unified_index = connections[self.connection_alias].get_unified_index()
        indexed_models = unified_index.get_indexed_models()

        for raw_result in raw_results.get('hits', {}).get('hits', []):
            source = raw_result['_source']
            app_label, model_name = source[DJANGO_CT].split('.')
            additional_fields = {}
            model = haystack_get_model(app_label, model_name)

            if model and model in indexed_models:
                for key, value in source.items():
                    index = unified_index.get_index(model)
                    string_key = str(key)

                    if string_key in index.fields and hasattr(index.fields[string_key], 'convert'):
                        additional_fields[string_key] = index.fields[string_key].convert(value)
                    else:
                        additional_fields[string_key] = self._to_python(value)

                del(additional_fields[DJANGO_CT])
                del(additional_fields[DJANGO_ID])

                if 'highlight' in raw_result:
                    additional_fields['highlighted'] = raw_result['highlight']

                if distance_point:
                    additional_fields['_point_of_origin'] = distance_point

                    if geo_sort and raw_result.get('sort'):
                        from haystack.utils.geo import Distance
                        additional_fields['_distance'] = Distance(km=float(raw_result['sort'][0]))
                    else:
                        additional_fields['_distance'] = None

                result = result_class(app_label, model_name, source[DJANGO_ID], raw_result['_score'],
                                      **additional_fields)
                results.append(result)
            else:
                hits -= 1

        return {
            'results': results,
            'hits': hits,
            'facets': facets,
            'spelling_suggestion': spelling_suggestion,
        }

    def get_filter_lookup(self, expression):
        """Parses an expression and determines the field and filter type."""
        parts = expression.split(FILTER_SEPARATOR)
        field = parts[0]
        if len(parts) == 1 or parts[-1] not in VALID_FILTERS:
            filter_type = 'content'
        else:
            filter_type = parts.pop()

        return (field, filter_type)


class Elasticsearch5SearchQuery(ElasticsearchSearchQuery):

    def __init__(self, using=DEFAULT_ALIAS):
        self.boost_fields = {}
        self.boost_negative = []
        self.filter_context = []
        super(Elasticsearch5SearchQuery, self).__init__(using=using)

    def build_query(self):
        """Adds parameters to the filter context.
        """
        final_query = self.matching_all_fragment()

        if self.boost:
            boost_list = []

            for boost_word, boost_value in self.boost.items():
                boost_list.append(self.boost_fragment(boost_word, boost_value))

            final_query = "%s %s" % (final_query, " ".join(boost_list))

        self.build_filter_context(self.query_filter)

        return final_query

    def build_filter_context(self, query_filter):
        for f in query_filter.children:
            if isinstance(f, SearchNode):
                self.build_filter_context(f)
            else:
                filter_query = {f[0]: f[1]}
                if filter_query not in self.filter_context:
                    self.filter_context.append({f[0]: f[1]})

    def build_params(self, spelling_query=None, **kwargs):
        search_kwargs = super(Elasticsearch5SearchQuery, self).build_params(spelling_query, **kwargs)
        if self.boost_fields:
            search_kwargs['boost_fields'] = self.boost_fields
        if self.boost_negative:
            search_kwargs['boost_negative'] = self.boost_negative
        if self.filter_context:
            search_kwargs['filter_context'] = self.filter_context
        return search_kwargs

    def add_boost_fields(self, fields):
        """Add boosted fields to the query."""
        self.boost_fields = fields

    def add_boost_negative(self, query, negative_boost):
        """Add negative boost to the query."""
        self.boost_negative = [query, negative_boost]

    def _clone(self, klass=None, using=None):
        clone = super(Elasticsearch5SearchQuery, self)._clone(klass, using)
        clone.boost_fields = self.boost_fields.copy()
        clone.boost_negative = self.boost_negative.copy()
        clone.filter_context = self.filter_context.copy()
        return clone


class Elasticsearch5SearchEngine(BaseEngine):
    backend = Elasticsearch5SearchBackend
    query = Elasticsearch5SearchQuery
