import collections
import inspect
from collections import namedtuple
from typing import Type, Union, TypeVar, Iterable, List, Dict, Callable, Any, Optional, ForwardRef

T = TypeVar("T")


def add(obj, deep=True):
    return _repository.get(_Repository).add(obj, deep=deep)


def that(cls_or_str: Union[Type[T], str]) -> T:
    return _repository.get(_Repository).get(cls_or_str)


def later(cls_or_str):
    """For use with descriptor based injection, lazy evaluation of dependency"""
    ...


def dependency(cls: Type[T]) -> Type[T]:
    """Either use as a decorator to register a class, or use during configuration"""
    _repository.get(_Repository).register(cls)
    return cls


# TODO: add functionality for not storing objects
def register(cls: Type[T], obj=None, factory=None, **kwargs):
    """
    :param cls:
    :param obj: Optional instance of type cls to add
    :param factory: Optional factory to create an instance
    :param kwargs: additional keyword arguments to pass to the factory (or cls.__init__) for
        construction
    """


# TODO This is going to be the messy part, support business logic
def setup(clean_up=False):
    """Setup and configure your Repository"""


def add_resolver(resolver: "Resolver"):
    _repository.get(_Repository).add_resolver(resolver)


def remove(obj):
    ...


def current_repo():
    return _repository.get(_Repository)


EMPTY = object()
DependencyInfo = namedtuple("DependencyInfo", ["cls", "factory", "kwargs"], defaults=(None,))
TypeHintInfo = namedtuple("TypeHintInfo", ["collection", "inner_type"])


class CannotResolve(Exception):
    pass


class PartiallyResolved(Exception):
    pass


class CircularDependeny(Exception):
    pass


class Resolver:
    def create(
        self, factory: Callable[..., T], repository: "_Repository", kwargs: dict = None
    ) -> T:
        kwargs = kwargs or {}
        deps = self.get_dependencies(factory, repository, kwargs)
        deps.update(kwargs)
        return factory(**deps)

    def get_dependencies(
        self, factory: Callable[..., T], repository: "_Repository", kwargs: dict = None
    ) -> Dict[str, Any]:
        raise CannotResolve()


class TypeHintingResolver(Resolver):
    def get_dependencies(
        self, factory: Callable[..., T], repository: "_Repository", kwargs: dict = None
    ) -> Dict[str, Any]:
        kwargs = kwargs or {}

        signature = inspect.signature(factory)

        dependencies = {}
        for key, param in signature.parameters.items():
            if key in kwargs or param.default is not inspect.Parameter.empty:
                continue
            annotation = param.annotation
            if annotation is inspect.Parameter.empty:
                raise CannotResolve(key)
            if hasattr(annotation, "__origin__"):
                info = parse_collection_from_type_hint(annotation)
                if info:
                    dependencies[key] = info.collection(repository.get(info.inner_type, many=True))
                    continue
                else:
                    raise CannotResolve(key, param.annotation)
            dependencies[key] = repository.get(param.annotation)
        return dependencies


class DefaultResolver(Resolver):
    def get_dependencies(
        self, factory: Callable[..., T], repository: "_Repository", kwargs: dict = None
    ) -> Dict[str, Any]:
        return {}


class _LookupStack(list):
    def push(self, item):
        self.append(item)
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.pop()

    def __str__(self):

        return " -> ".join(getattr(i, "__name__", str(i)) for i in self)

# TODO: Layer repositories in contexts
class _Repository:
    def __init__(self, plugins: Iterable["Resolver"]):

        self.resolvers: List["Resolver"] = list(plugins)
        self.types_by_str: Dict[str, Type[T]] = {}
        self.types: Dict[Type, DependencyInfo] = {}
        self.instances: Dict[Type[T], List[T]] = {}
        self.lookup_stack = _LookupStack()

    def get(self, key: Union[Type[T], str], many=False) -> Union[List[T], T]:
        if isinstance(key, str):
            key = self.types_by_str.get(key)
        if key is None:
            raise CannotResolve(f"Could not resolve for key {key}")

        if key not in self.instances:
            self.create(key)

        instances = self.instances[key]
        if many:
            return instances
        else:
            return instances[-1]

    def create(self, key: Type[T]) -> T:
        if not isinstance(key, type):
            raise TypeError(f"Can only create classes, not {key}")
        if key in self.lookup_stack:
            raise CircularDependeny(str(self.lookup_stack))
        info = self._ensure_info(key)
        inst = EMPTY
        with self.lookup_stack.push(key):
            for plugin in self.resolvers:
                try:
                    inst = plugin.create(info.factory, self, info.kwargs)
                except CannotResolve:
                    continue
                break
            if inst is EMPTY:
                raise CannotResolve(self.lookup_stack)
            self.add(inst)
            return inst

    def _ensure_info(self, cls: Type[T]) -> DependencyInfo:
        info = self.types.get(cls)
        if info:
            return info
        self.register(cls)
        return self._ensure_info(cls)

    def add(self, inst, deep=True):
        def append_instance_to(key):
            if key not in self.instances:
                self.instances[key] = []
            self.instances[key].append(inst)

        cls = type(inst)
        self.register(cls)
        append_instance_to(cls)
        if deep:
            for base in cls.__mro__[1:]:
                append_instance_to(base)

    def register(self, cls: Type[T], factory: Callable = None, kwargs=None):
        if not isinstance(cls, type):
            raise TypeError(f"Can only register classes, not {cls}")
        if factory is None:
            factory = cls
        for base in cls.__mro__:
            if base not in self.types:
                key = base.__name__
                self.types_by_str[key] = base
                self.types[base] = DependencyInfo(cls=cls, factory=factory, kwargs=kwargs)

    def add_resolver(self, resolver: Resolver):
        self.resolvers.insert(0, resolver)

    def __contains__(self, item: Type):
        return item in self.instances


def is_generic_type_hint(hint):
    return hasattr(hint, "__origin__")


def parse_collection_from_type_hint(hint) -> Optional[TypeHintInfo]:
    """
    Get the constructor for iterable/sequence type hints:
    returns the concrete type belonging to the type hint, ie `set` for `typing.Set`

    for the abstract type hints typing.Iterable
    :param hint: A Generic Type hint
    :returns: TypeHintInfo, or None if it could not be parsed into a list-like collection of
    `type`. eg for nested generic types (`List[List[int]])
    """
    # hint must be a Type hint of type Iterable, but not a Mapping
    if (
        not is_generic_type_hint(hint)
        or not issubclass(hint.__origin__, collections.abc.Iterable)
        or issubclass(hint.__origin__, collections.abc.Mapping)
    ):
        return None

    collection = hint.__origin__
    if issubclass(collection, tuple):
        # Must be variable length tuple
        if len(hint.__args__) != 2 or hint.__args__[1] != Ellipsis:
            return None
    elif len(hint.__args__) != 1:
        return None
    if collection in vars(collections.abc).values():
        collection = list

    inner_type = hint.__args__[0]
    if isinstance(inner_type, ForwardRef):
        inner_type = inner_type.__forward_arg__
    if not isinstance(inner_type, (str, type)):
        return None

    return TypeHintInfo(collection, inner_type)


_repository = _Repository(plugins=[TypeHintingResolver(), DefaultResolver()])
_repository.add(TypeHintingResolver())

# Some aliases for professional (ie. boring) people
get = that
attribute = later
