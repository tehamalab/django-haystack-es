=============================
Django Haystack ES
=============================

.. image:: https://badge.fury.io/py/django-haystack-es.svg
    :target: https://badge.fury.io/py/django-haystack-es

.. image:: https://travis-ci.org/tehamalab/django-haystack-es.svg?branch=master
    :target: https://travis-ci.org/tehamalab/django-haystack-es

.. image:: https://codecov.io/gh/tehamalab/django-haystack-es/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/tehamalab/django-haystack-es

Extended haystack backend for Elasticsearch.
Currently tested with Elasticsearch 5.X only.


Quickstart
----------

Install Django Haystack ES::

    pip install django-haystack-es

Add ``haystack_es.ElasticsearchSearchEngine`` to your ``HAYSTACK_CONNECTIONS`` engine in ``settings.py``

.. code-block:: python

    HAYSTACK_CONNECTIONS = {
        'default': {
            'ENGINE': 'haystack_es.Elasticsearch5SearchEngine',
            'URL': 'http://127.0.0.1:9200/',
            'INDEX_NAME': 'my_index_name',
        }
    }

Define your indexes using ``haystack_es.indexes`` instead of ``haystack.indexes``

.. code-block:: python

    # myapp/search_indexes.py

    from haystack_es import indexes
    from myapp.models import MyModel


    class MyModelIndex(indexes.SearchIndex, indexes.Indexable):
        foo = indexes.CharField(document=True, use_template=True)
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
