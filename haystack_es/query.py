from haystack.query import SearchQuerySet as BaseSearchQuerySet


class SearchQuerySet(BaseSearchQuerySet):

    def boost_fields(self, fields):
        """Boosts fields."""
        clone = self._clone()
        clone.query.add_boost_fields(fields)
        return clone
