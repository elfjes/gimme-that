from typing import Union, Type, TYPE_CHECKING

from gimme.repository import LayeredRepository, SimpleRepository, Attribute
from gimme.resolvers import TypeHintingResolver
from gimme.types import DependencyInfo, T

if TYPE_CHECKING:
    from gimme.resolvers import Resolver


def that(cls_or_str: Union[Type[T], str]) -> T:
    """Request an object either by type or by type name"""
    return current_repo().get(cls_or_str)


def later(cls_or_str: Union[type, str], lazy=True) -> "Attribute":
    """For use with descriptor based injection, allows for lazy evaluation of a dependency"""
    return Attribute(cls_or_str, repo=current_repo(), lazy=lazy)


def add(obj, deep=True):
    """add an object to the Repository

    :param obj: the object to add
    :param deep: whether to also register `obj` for all base classes of `obj`
    :return:
    """
    return current_repo().add(obj, deep=deep)


def dependency(cls: Type[T]) -> Type[T]:
    """Either use as a decorator to register a class, or use during configuration"""
    current_repo().register(cls)
    return cls


def register(cls: Type[T] = None, factory=None, info=None, store=True, kwargs=None):
    """
    :param cls:
    :param factory: Optional factory to create an instance
    :param info:
    :param store:
    :param kwargs: additional keyword arguments to pass to the factory (or cls.__init__) for
        construction
    """
    current_repo().register(cls, factory, info=info, store=store, kwargs=kwargs)


def setup(objects=None, types=None, resolvers=None):
    """Setup and configure your Repository"""
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


def add_resolver(resolver: "Resolver"):
    current_repo().add_resolver(resolver)


def current_repo():
    return _repository.get(LayeredRepository)


def context():
    """return a context manager that adds a repository to the stack and yields it"""
    repo = current_repo()
    resolvers = repo.resolvers.copy()
    return repo.push(SimpleRepository(resolvers))


def pop_context():
    """pops the current repository from the repository stack, effectively resetting the state of
    the repository to a previous state"""
    repo = current_repo()
    return repo.pop()


_repository = SimpleRepository(resolvers=[TypeHintingResolver()])
_repository.add(TypeHintingResolver())

# Some aliases for professional (ie. boring) people
get = that
attribute = later
