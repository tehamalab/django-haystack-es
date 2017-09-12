from haystack.query import SearchQuerySet as BaseSearchQuerySet


class SearchQuerySet(BaseSearchQuerySet):

    def boost_fields(self, fields):
        """Boosts fields."""
        clone = self._clone()
        clone.query.add_boost_fields(fields)
        return clone

    def boost_negative(self, query, negative_boost):
        """Boost negatively."""
        clone = self._clone()
        clone.query.add_boost_negative(query, negative_boost)
        return clone
