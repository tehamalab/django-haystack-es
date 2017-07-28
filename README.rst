=============================
Django Haystack ES
=============================

.. image:: https://badge.fury.io/py/django-haystack-es.svg
    :target: https://badge.fury.io/py/django-haystack-es

.. image:: https://travis-ci.org/tehamalab/django-haystack-es.svg?branch=master
    :target: https://travis-ci.org/tehamalab/django-haystack-es

.. image:: https://codecov.io/gh/tehamalab/django-haystack-es/branch/master/graph/badge.svg
    :target: https://codecov.io/gh/tehamalab/django-haystack-es

Extended haystack backend for Elasticsearch

Documentation
-------------

The full documentation is at https://django-haystack-es.readthedocs.io.

Quickstart
----------

Install Django Haystack ES::

    pip install django-haystack-es

Add it to your `INSTALLED_APPS`:

.. code-block:: python

    INSTALLED_APPS = (
        ...
        'haystack_es.apps.HaystackEsConfig',
        ...
    )

Add Django Haystack ES's URL patterns:

.. code-block:: python

    from haystack_es import urls as haystack_es_urls


    urlpatterns = [
        ...
        url(r'^', include(haystack_es_urls)),
        ...
    ]

Features
--------

* TODO

Running Tests
-------------

Does the code actually work?

::

    source <YOURVIRTUALENV>/bin/activate
    (myenv) $ pip install tox
    (myenv) $ tox

Credits
-------

Tools used in rendering this package:

*  Cookiecutter_
*  `cookiecutter-djangopackage`_

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`cookiecutter-djangopackage`: https://github.com/pydanny/cookiecutter-djangopackage
