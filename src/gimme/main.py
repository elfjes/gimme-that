from typing import Union, Type, Any, Callable, Optional, Iterable

from gimme.repository import LayeredRepository, SimpleRepository, Attribute
from gimme.resolvers import Resolver, TypeHintingResolver
from gimme.types import DependencyInfo, T


def that(cls_or_str: Union[Type[T], str]) -> T:
    """Request an object from the :class:`Repository <gimme.repository.LayeredRepository>` by type.
    If it does not exist in the :class:`Repository <gimme.repository.LayeredRepository>` yet,
    it will be created, and any dependencies of the class will be resolved recursively. If the
    class has been registered with a specific factory function, that function will be used to
    create the object.

    Optionally, if the class has been registered using the :func:`gimme.dependency` decorator or
    :func:`gimme.register` function, the object type may also be specified using class name as a
    string.

    :param cls_or_str: The type of which to retrieve an object
    :rtype: ~T
    """
    return current_repo().get(cls_or_str)


def later(cls_or_str: Union[type, str], lazy: bool = True) -> "Attribute":
    """Use this as a descriptor in your class definition when dealing with circular dependencies.
    Normally, having circular dependencies would prevent instantiating these classes.

    By default, using this descriptor to specify a dependency defers the resolution of this
    dependency until the first time it is used.

    :param cls_or_str: The type of which to retrieve an object
    :param lazy: When set to ``False``, the dependency is resolved immediately the first time the
        dependent class is instantiated. This precludes the use of ``gimme.later`` for resolving
        circular dependencies, but instead now it works the same way of using type annotations for
        specifying dependencies. If you don't like using type annotations, you may use
        ``gimme.later`` with ``lazy=False`` to get the same behaviour.
    """
    return Attribute(cls_or_str, repo=current_repo(), lazy=lazy)


def add(obj: Any, deep: bool = True):
    """Add an object to the :class:`Repository <gimme.repository.LayeredRepository>` after which
    it will be available for dependent classes when resolving their dependencies.

    By default, the object will be registered for both its own class as well as any subclasses (up
    to and including ``object``). Setting ``deep=False`` switches this off, and the object will
    only be registered for its own class

    :param obj: The object to add to the :class:`Repository <gimme.repository.LayeredRepository>`
    :param deep: Whether to also register `obj` for all base classes of `obj`
    """
    return current_repo().add(obj, deep=deep)


def dependency(cls: Type[T]) -> Type[T]:
    """
    .. deprecated:: 0.1.2
        Use :func:`gimme.register` instead.
    """
    current_repo().register(cls)
    return cls


def register(
    cls: type = None,
    factory: Optional[Callable] = None,
    info: Optional[DependencyInfo] = None,
    store: bool = True,
    kwargs: Optional[dict] = None,
):
    """
    Register a class in the :class:`Repository <gimme.repository.LayeredRepository>`. This makes
    the class available for identification by string (see :func:`gimme.that` and
    :func:`gimme.later`) and allows for additional control over class instantiation.

    Alternatively, instead of giving a class (and optional parameters), you can also give a
    :class:`~gimme.types.DependencyInfo` object directly that contains the configuration.

    :param cls: The class to register in the repository.
    :param factory: Optional factory to create an instance, if not specified, use the class'
        constructor instead (ie. ``cls.__init__``)
    :param info: An object that contains the class instantiation configuration. Only provide this
        when no ``cls`` parameter is given
    :param store: Whether to store an instantiated class in the
        :class:`Repository <gimme.repository.LayeredRepository>`. The default effectively makes
        every class a singleton, but if you want to change this behaviour, set ``store=False``
    :param kwargs: Additional keyword arguments to pass to the factory (or ``cls.__init__``) for
        construction
    """
    current_repo().register(cls, factory, info=info, store=store, kwargs=kwargs)


def setup(
    objects: Optional[Iterable[Any]] = None,
    types: Optional[Iterable[Union[type, DependencyInfo]]] = None,
    resolvers: Optional[Iterable[Resolver]] = None,
):
    """Setup and configure your :class:`Repository <gimme.repository.LayeredRepository>`

    :param objects: Any objects to add to the
        :class:`Repository <gimme.repository.LayeredRepository>`
    :param types: Any types / classes to register
    :param resolvers: Any additional :class:`Resolvers <gimme.resolvers.Resolver>` to add for
        dependency resolution
    """
    if objects is not None:
        for obj in objects:
            add(obj)

    if types is not None:
        for tp in types:
            if isinstance(tp, DependencyInfo):
                register(info=tp)
            else:
                register(cls=tp)
    if resolvers is not None:
        for resolver in resolvers:
            add_resolver(resolver)


def add_resolver(resolver: Resolver):
    """Add a custom :class:`~gimme.resolvers.Resolver` to the
    :class:`Repository <gimme.repository.LayeredRepository>`
    """
    current_repo().add_resolver(resolver)


def current_repo() -> LayeredRepository:
    return _repository.get(LayeredRepository)


def context():
    """return a context manager that adds a repository to the stack and yields it"""
    repo = current_repo()
    resolvers = repo.resolvers.copy()
    return repo.push(SimpleRepository(resolvers))


def pop_context():
    """Pops the current repository from the repository stack, effectively resetting the state of
    the repository to a previous state"""
    repo = current_repo()
    return repo.pop()


_repository = SimpleRepository(resolvers=[TypeHintingResolver()])
_repository.add(TypeHintingResolver())

# Some aliases for professional (ie. boring) people
get = that
attribute = later
