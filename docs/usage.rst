=====
Usage
=====

To use Django Haystack ES in a project, add it to your `INSTALLED_APPS`:

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
