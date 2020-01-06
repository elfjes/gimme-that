.. Gimme That documentation master file, created by
   sphinx-quickstart on Tue Dec 24 13:59:31 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Gimme That's documentation!
======================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

API reference
===================

Main API
########
.. automodule:: gimme
   :members: add, add_resolver, context, dependency, later, pop_context,register, setup, that

.. function:: get(cls_or_str)

   An alias for :func:`gimme.that`. Use this if you do not like the default *cute* names

.. function:: attribute(cls_or_str)

   An alias for :func:`gimme.later`. Use this if you do not like the default *cute* names

gimme.repository
################
.. automodule:: gimme.repository
   :members:

gimme.resolvers
###############
.. automodule:: gimme.resolvers
   :members: Resolver

gimme.helpers
#############
.. automodule:: gimme.helpers
   :members:

gimme.exceptions
################
.. automodule:: gimme.exceptions
   :members:

gimme.types
###########
.. automodule:: gimme.types
   :members:
