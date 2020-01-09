Why dependency injection?
=========================

A often heard argument is that Python doesn't need dependency injection (DI) because it is a
dynamically typed language. I've always found this a confusing argument, possibly coming from
those who think that DI is only useful when substituting (ie. mocking out) classes during (unit)
testing. While testing is a good use case for having DI, it is by far not the only reason you'd
want to use DI. Let's go over the reasons why DI is a good thing that makes your code cleaner,
more loosely (looselier?) coupled. But before we do that, look at what it is exactly.

What is dependency injection?
-----------------------------
Let's consider the following situation: We have a service called ``MySQLConnection`` which is being
consumed, as a dependency, by another class: ``Client``. Without using dependency
injection we could write this as the following:

.. code-block:: python

    class MySQLConnection:
        def cursor(self):
            ...


    class Client:
        def __init__(self):
            self.connection = MySQLConnection()

        def do_something(self):
            cursor = self.connection.cursor()
            ...

While this works, there are a couple of issues with this approach. We have tied our
``Client`` to a specific implementation of ``Service``. This makes ``Client``
tightly coupled to ``Service``, meaning that we have no way of substituting it with a different
implementation of ``Service``. At first, this may not be a problem. We only need to substitute our
``Service`` during testing, so we just mock it out:

.. code-block:: python

    from unittest import mock


    @mock.patch("__main__.MySQLConnection")
    def test_our_consumer(MySQLConnection):
        client = Client()
        client.do_something()
        client.connection.cursor.assert_called()

Hurray, we have successfully swapped out our dependency with a mock version of it without
DI. Take that, DI!

But what happens when our program grows and evolves? We continue developing our program and create
a bunch of other classes that depend on our database connection. Afterwards, we decide to change
our database technology to PostgreSQL. We create a new ``PostgreSQLConnection`` class, and, being
the good OOP developers that we are, even create a base class for a database connection, that both
``MySQLConnection`` and ``PostgreSQLConnection`` inherit from:

.. code-block:: python

    class DBConnection:
        def cursor(self):
            raise NotImplementedError


    class MySQLConnection(DBConnection):
        def cursor(self):
            ...


    class PostgreSQLConnection(DBConnection):
        def cursor(self):
            ...

We now have to change all classes that use our database connection to use the
``PostgreSQLConnection``, *AND* change all our tests to mock it out. Let's instead write a little
helper/factory function that we can ask for a database connection:

.. code-block:: python

    def get_db_connection() -> DBConnection:
        # TODO: we should make this configurable through a config module or something
        connection_cls = PostgreSQLConnection
        return connection_cls()


    class Client:
        def __init__(self):
            self.connection = get_db_connection()

        ...

We're now asking an external object (our factory function) for the dependency. This is one form of
dependency injection, albeit a crude one. For every dependency we have in our program, we need a
separate factory function. And this could get quite messy. Also, we're still tightly coupled to
our factory functions. During our tests we still need to mock them out for all classes that use
the helpers. We can make it a bit more generic and create an entity that we can ask for
objects of any type, and it should give us an instance of whatever we ask for. Congratulations, we
have now developed a Service Locator. A very simple implementation is given below:

.. code-block:: python

    service_locator = {
        DBConnection: PostgreSQLConnection(),
    }


    class Client:
        def __init__(self):
            self.connection = service_locator[DBConnection]

        ...

That's right, just a dictionary that we populate beforehand with all our dependencies. This is the
heart of the Service Locator pattern. You register some objects, and these will be provided when
you ask for query it by type. A more sophisticated version also might also be configured on how
to instantiate an object that's not yet available and might infer a registered object's base
types instead of having to provide it explicitly. We are still however, strongly dependent on an
external entity; no longer the factory function, but now the ``service_locator``. We can configure
the service locator based on what we need, like choose the implementation of our dependencies for
both tests and production, but it's still not ideal. For example, during our tests, we need to make
sure we setup and cleanup the ``service_locator`` with the right

What if we go about it in a different way? What if, instead of asking for a dependency from inside
our ``Client`` class, we provide it to the class when we instantiate it:

.. code-block:: python

    class Client:
        def __init__(self, connection: DBConnection):
            self.connection = connection

        ...


The class is now loosely coupled to its dependency and has no coupling to our service locator or
factory functions. This is arguably the cleanest way of implementing dependency injection. It does
however, create a new problem. How and where are we going to instantiate our ``Client`` class? We
can no longer just type ``Client`` and be done with it. We need to know about its dependencies. One
way we can solve this