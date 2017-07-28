# -*- coding: utf-8

from haystack.fields import SearchField, CharField


class DictField(SearchField):
    field_type = 'dict'

    def prepare(self, obj):
        return self.convert(super(DictField, self).prepare(obj))

    def convert(self, value):
        if value is None:
            return None
        return dict(value)


class NestedField(SearchField):
    field_type = 'nested'

    def __init__(self, **kwargs):
        super(NestedField, self).__init__(**kwargs)
        self.is_multivalued = True

    def prepare(self, obj):
        return self.convert(super(NestedField, self).prepare(obj))

    def convert(self, value):
        if value is None:
            return None
        values = []
        for obj in value:
            for k, v in obj.items():
                if hasattr(v, 'strftime'):
                    obj[k] = v.isoformat()
            values.append(obj)
        return values


class NgramField(CharField):
    field_type = 'ngram'


class EdgeNgramField(NgramField):
    field_type = 'edge_ngram'
