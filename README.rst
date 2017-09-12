=============================
Django Haystack ES
=============================

.. image:: https://badge.fury.io/py/django-haystack-es.svg
    :target: https://badge.fury.io/py/django-haystack-es

.. image:: https://travis-ci.org/tehamalab/django-haystack-es.svg?branch=master
    :target: https://travis-ci.org/tehamalab/django-haystack-es

.. image:: https://codecov.io/gh/tehamalab/django-haystack-es/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/tehamalab/django-haystack-es

Django Haystack backend for Elasticsearch 5.


Quickstart
----------

Install Django Haystack ES::

    pip install django-haystack-es

Add ``haystack_es.backends.ElasticsearchSearchEngine`` to your ``HAYSTACK_CONNECTIONS`` engine in ``settings.py``

Example

.. code-block:: python

    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'haystack_es.backends.Elasticsearch5SearchEngine',
            # ...
        }
    }

Define your indexes using ``haystack_es.indexes`` instead of ``haystack.indexes``.

Example

.. code-block:: python

    # myapp/search_indexes.py

    from haystack_es import indexes
    from myapp.models import MyModel


    class MyModelIndex(indexes.SearchIndex, indexes.Indexable):
        text = indexes.CharField(document=True, use_template=True)
        # ...

If you have `celery-haystack <http://celery-haystack.readthedocs.org/>`_ installed you can use
``haystack_es.indexes.CelerySearchIndex`` for defining your SearchIndex utilizing celery-haystack

If you want to utilize additional SearchQuerySet methods use ``haystack_es.query.SearchQuerySet``
instead of ``haystack.query.SearchQuerySet``.

Example

.. code-block:: python

    from haystack_es.query import SearchQuerySet

    sqs = SearchQuerySet().filter(content='some query')
    sqs.boost_fields({'field_name': 2, 'some_field': 1.5, 'another_field': 1})
    sqs.facet('some_field')
    # ...


Differences compared to the default django-haystack Elasticsearch backend
---------------------------------------------------------------------------

* Intended for Elasticsearch >= 5
* Allows query-time fields boosting.
* Allows query-time
  `negative boost <https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-boosting-query.html>`_ 
* Provides additional SearchFields; ``DictField``, ``NestedField`` and ``GeometryField``
* Tries to use Elasticsearch
  `filter context <https://www.elastic.co/guide/en/elasticsearch/reference/current/query-filter-context.html>`_
  instead of query string for filtering results.
* Uses `multi-fields <https://www.elastic.co/guide/en/elasticsearch/reference/current/multi-fields.html>`_
  for creating shadow fields which are useful for performing operations like
  faceting and exact matches which need non-analyzed values.

Query-time fields boosting
----------------------------

::

    from haystack_es.query import SearchQuerySet
    SearchQuerySet().boost_fields(boost_fields)


Example ``SearchQuerySet().boost_fields({'field_name': 2, 'another_field': 1})``


Negative boosting
------------------

::

    from haystack_es.query import SearchQuerySet
    SearchQuerySet().boost_negative(query, negative_boost)


example
``SearchQuerySet().boost_negative({'match': {'category.raw': 'awful type'}}, negative_boost)``


Running Tests
-------------

Does the code actually work?

::

    source <YOURVIRTUALENV>/bin/activate
    (myenv) $ pip install tox
    (myenv) $ tox

Credits
-------

Inspired by

* `haystack-elasticsearch5`: https://github.com/Alkalit/haystack-elasticsearch5

Tools used in rendering this package:

*  Cookiecutter_
*  `cookiecutter-djangopackage`_

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`cookiecutter-djangopackage`: https://github.com/pydanny/cookiecutter-djangopackage
