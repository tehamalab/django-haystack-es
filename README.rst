=============================
Django Haystack ES
=============================

.. image:: https://badge.fury.io/py/django-haystack-es.svg
    :target: https://badge.fury.io/py/django-haystack-es

.. image:: https://travis-ci.org/tehamalab/django-haystack-es.svg?branch=master
    :target: https://travis-ci.org/tehamalab/django-haystack-es

.. image:: https://codecov.io/gh/tehamalab/django-haystack-es/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/tehamalab/django-haystack-es

Extended Haystack backend for Elasticsearch 5.


Quickstart
----------

Install Django Haystack ES::

    pip install django-haystack-es

Add ``haystack_es.ElasticsearchSearchEngine`` to your ``HAYSTACK_CONNECTIONS`` engine in ``settings.py``

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

If you want to utilize additional SearchQuerySet methods use ``haystack_es.query.SearchQuerySet``
instead of ``haystack.query.SearchQuerySet``.

Example

.. code-block:: python

    from haystack_es.query import SearchQuerySet

    sqs = SearchQuerySet().filter(content='some query')
    sqs.boost_fields({'name': 2, 'some_field': 1.5, 'another_field': 1})
    sqs.facet('some_field')
    # ...

Running Tests
-------------

Does the code actually work?

::

    source <YOURVIRTUALENV>/bin/activate
    (myenv) $ pip install tox
    (myenv) $ tox

Credits
-------

Based on

* `haystack-elasticsearch5`: https://github.com/Alkalit/haystack-elasticsearch5

Tools used in rendering this package:

*  Cookiecutter_
*  `cookiecutter-djangopackage`_

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`cookiecutter-djangopackage`: https://github.com/pydanny/cookiecutter-djangopackage
