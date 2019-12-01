import inspect
from collections import namedtuple
from typing import (
    Type,
    Union,
    TypeVar,
    Iterable,
    List,
    Dict,
    Callable,
    Optional,
    Any,
)

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


def remove(obj):
    ...


def current_repo():
    return _repository.get(_Repository)


EMPTY = object()
DependencyInfo = namedtuple("DependencyInfo", ["cls", "factory", "kwargs"], defaults=(None,))


class CannotResolve(Exception):
    pass


class PartiallyResolved(Exception):
    pass


class BasePlugin:
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


class TypeHintingPlugin(BasePlugin):
    # TODO check that kwargs are actually parameters
    def get_dependencies(
        self, factory: Callable[..., T], repository: "_Repository", kwargs: dict = None
    ) -> Dict[str, Any]:
        kwargs = kwargs or {}

        signature = inspect.signature(factory)

        dependencies = {}
        for key, param in signature.parameters.items():
            if key in kwargs or param.default is not inspect.Parameter.empty:
                continue
            if param.annotation is inspect.Parameter.empty:
                raise CannotResolve(key)
            dependencies[key] = repository.get(param.annotation)
        return dependencies


class DefaultPlugin(BasePlugin):
    def get_dependencies(
        self, factory: Callable[..., T], repository: "_Repository", kwargs: dict = None
    ) -> Dict[str, Any]:
        return {}


class DataclassPlugin(BasePlugin):
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
        from dataclasses import is_dataclass, MISSING, fields

        if not (is_dataclass(factory) and isinstance(factory, type)):
            raise CannotResolve()

        kwargs = kwargs or {}
        dependencies = {}
        for field in fields(factory):
            if (
                field.name in kwargs
                or not field.init
                or field.default is not MISSING
                or field.default_factory is not MISSING
            ):
                continue
            dependencies[field.name] = repository.get(field.type)
        return dependencies


class AttributePlugin(BasePlugin):
    ...


# TODO: Detect circular dependencies
# TODO: Support adding and retrieving Sequence of dependencies (for use with plugins)
class _Repository:
    def __init__(self, plugins: Iterable["BasePlugin"] = EMPTY, use_default_plugins=True):
        if plugins is EMPTY:
            plugins = []

        self.plugins: List["BasePlugin"] = list(plugins)
        if use_default_plugins:
            self.plugins.extend([TypeHintingPlugin(), DefaultPlugin()])

        self.types_by_str: Dict[str, Type[T]] = {}
        self.types: Dict[Type, DependencyInfo] = {}
        self.instances: Dict[Type[T], T] = {}

    def get(self, key: Union[Type[T], str]) -> T:
        if isinstance(key, str):
            key = self.types_by_str.get(key)
        if key is None:
            raise CannotResolve(f"Could not resolve for key {key}")

        if key in self.instances:
            return self.instances[key]

        return self.create(key)

    def create(self, key: Type[T]) -> T:
        info = self._ensure_info(key)
        inst = EMPTY
        for plugin in self.plugins:
            try:
                inst = plugin.create(info.factory, self, info.kwargs)
            except CannotResolve:
                continue
            break
        if inst is EMPTY:
            raise CannotResolve(str(key))
        self.add(inst)
        return inst

    def _ensure_info(self, cls: Type[T]) -> DependencyInfo:
        info = self.types.get(cls)
        if info:
            return info
        self.register(cls)
        return self._ensure_info(cls)

    def add(self, inst, deep=True):
        cls = type(inst)
        self.register(cls)
        self.instances[cls] = inst
        if deep:
            for base in cls.__mro__[1:]:
                self.instances[base] = inst

    def register(self, cls: Type[T], factory: Callable = None, kwargs=None):
        if factory is None:
            factory = cls
        for base in cls.__mro__:
            if base not in self.types:
                key = base.__name__
                self.types_by_str[key] = cls
                self.types[base] = DependencyInfo(cls=cls, factory=factory, kwargs=kwargs)

    # TODO Maybe remove
    def _as_type(self, key: Union[Type[T], str]) -> Optional[Type[T]]:
        if isinstance(key, str):
            return self.types_by_str.get(key)
        return key

    # TODO Maybe remove
    @staticmethod
    def _as_str(cls_or_name: Union[Type, str]) -> str:
        if isinstance(cls_or_name, type):
            return cls_or_name.__name__
        elif isinstance(cls_or_name, str):
            return cls_or_name
        else:
            raise TypeError("types must be given as a class or a string")

    def __contains__(self, item: Type):
        return item in self.instances


_repository = _Repository()

# Some aliases for professional (ie. boring) people
get = that
attribute = later
