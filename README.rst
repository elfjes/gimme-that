.. image:: https://dev.azure.com/pellekoster/gimme-that/_apis/build/status/elfjes.gimme-that?branchName=master
  :target: https://dev.azure.com/pellekoster/gimme-that/_build?definitionId=1
  :alt: Azure Pipelines

Gimme That
===========
A lightweight, simple but extensible dependency injection framework

Getting started
----------------
Install from `PyPI <www.pypi.org>`_

.. code-block::

    pip install gimme-that

Basic usage
#############

.. code-block:: python

    import gimme


    class MyService:
        pass


    class ServiceConsumer:
        def __init__(self, service: MyService):
            self.service = service


    # gimme.that automatically detects and resolves dependencies based on type annotations
    consumer = gimme.that(ServiceConsumer)

    isinstance(consumer.service, MyService)  # True

Features
--------
* Automatically detects dependencies based on type annotations
* Works with ``dataclass`` classes and ``attr.s``
* Class repository that stores created objects for re-use
* Register classes to provide additional configuration on how ``gimme.that`` should instantiate classes

  * Custom factory functions
  * Store or do not store created objects
  * Provide additional keyword arguments to the initializer

* Scoped repositories to manage the lifetime of created objects (useful for testing)
* Does not require any decorators or other additions to your classes (most of the time). They remain `your` classes
* Detects circular dependencies, and provides the means to resolve them
* Extensibility using plugins: create your own logic for resolving dependencies and creating classes

Development
------------
.. code-block::

    pip install -e .[dev]


