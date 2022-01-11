.. image:: https://github.com/elfjes/gimme-that/actions/workflows/main.yml/badge.svg?branch=master
  :target: https://github.com/elfjes/gimme-that/actions/workflows/main.yml
  :alt: Github Actions

.. image:: https://badge.fury.io/py/gimme-that.svg
  :target: https://pypi.org/project/gimme-that
  :alt: PyPI - Package version

.. image:: https://img.shields.io/pypi/pyversions/gimme-that
  :target: https://pypi.org/project/gimme-that
  :alt: PyPI - Python Version

.. image:: https://codecov.io/gh/elfjes/gimme-that/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/elfjes/gimme-that

.. image:: https://readthedocs.org/projects/gimme-that/badge/?version=latest
  :target: https://gimme-that.readthedocs.io/en/latest/
  :alt: Read the Docs

Gimme That
===========
A lightweight, simple but extensible dependency injection framework. Read the full documentation
`here <https://gimme-that.readthedocs.io>`_

Getting started
----------------
Install from `PyPI <https://pypi.org/project/gimme-that>`_

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
* Extensibility using plugins: create your own logic for resolving dependencies and instantiating classes

Development
------------
.. code-block::

    pip install -e .[dev]


