import collections
import inspect
from collections import namedtuple
from itertools import chain
from typing import Type, Union, TypeVar, Iterable, List, Dict, Callable, Any, Optional, ForwardRef

T = TypeVar("T")


def that(cls_or_str: Union[Type[T], str]) -> T:
    """Request an object either by type or by type name"""
    return current_repo().get(cls_or_str)


def later(cls_or_str, *, lazy=True):
    """For use with descriptor based injection, allows for lazy evaluation of dependency"""
    return Attribute(cls_or_str, lazy=lazy)


def add(obj, deep=True):
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


EMPTY = object()
DependencyInfo = namedtuple(
    "DependencyInfo", ["cls", "factory", "store", "kwargs"], defaults=(True, None,)
)
TypeHintInfo = namedtuple("TypeHintInfo", ["collection", "inner_type"])


class CannotResolve(TypeError):
    pass


class PartiallyResolved(RuntimeError):
    pass


class CircularDependency(RuntimeError):
    pass


class _ContextManagedStack(list):
    def push(self, item):
        self.append(item)
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.pop()


class _LookupStack(_ContextManagedStack):
    def __str__(self):
        return " -> ".join(getattr(i, "__name__", str(i)) for i in self)


class SimpleRepository:
    def __init__(self, resolvers: Iterable["Resolver"]):

        self.resolvers: List["Resolver"] = list(resolvers)
        self.types_by_str: Dict[str, Type[T]] = {}
        self.types: Dict[Type, DependencyInfo] = {}
        self.instances: Dict[Type[T], List[T]] = {}
        self.lookup_stack = _LookupStack()

    def get(self, key: Union[Type[T], str], many=False, repo=None) -> Union[List[T], T]:
        if isinstance(key, str):
            key = self.types_by_str.get(key)
        if key is None:
            raise CannotResolve(f"Could not resolve for key {key}")

        if many:
            return self.instances.get(key, [])

        if key not in self.instances:
            inst = self.create(key, repo=repo)
            return inst

        instances = self.instances[key]
        return instances[-1]

    def create(self, key: Type[T], repo=None) -> T:
        repo = repo or self
        if not isinstance(key, type):
            raise TypeError(f"Can only create classes, not {key}")
        if key in self.lookup_stack:
            raise CircularDependency(str(self.lookup_stack))
        info = self._ensure_info(key)
        inst = EMPTY
        with self.lookup_stack.push(key):
            for plugin in self.resolvers:
                try:
                    inst = plugin.create(info.factory, repo, info.kwargs)
                except (CannotResolve, PartiallyResolved):
                    continue
                break
            if inst is EMPTY:
                raise CannotResolve(str(self.lookup_stack))
            if info.store:
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

    def register(
        self,
        cls: Type[T] = None,
        factory: Callable = None,
        info: DependencyInfo = None,
        store=True,
        kwargs=None,
    ):
        if not (bool(cls) ^ bool(info)):
            raise ValueError("Supply either cls or info")

        if info is None:
            if not isinstance(cls, type):
                raise TypeError(f"Can only register classes, not {cls}")
            if factory is None:
                factory = cls
            info = DependencyInfo(cls=cls, factory=factory, store=store, kwargs=kwargs)

        for base in info.cls.__mro__:
            if base not in self.types:
                key = base.__name__
                self.types_by_str[key] = base
                self.types[base] = info

    def add_resolver(self, resolver: "Resolver"):
        self.resolvers.insert(0, resolver)

    def __contains__(self, item: Type):
        return item in self.instances


class LayeredRepository(_ContextManagedStack):
    def __init__(self, first_layer: SimpleRepository):
        super().__init__([first_layer])

    def current(self):
        return self[-1]

    def get(self, key: Union[Type[T], str], many=False) -> Union[List[T], T]:
        err = None

        if many:
            return list(chain.from_iterable(repo.get(key, many) for repo in self))

        for repo in reversed(self):
            try:
                return repo.get(key, many, repo=self)
            except CannotResolve as e:
                err = e
        if err:
            raise err

    def create(self, key: Type[T]) -> T:
        return self.current().create(key, repo=self)

    def pop(self):
        if len(self) <= 1:
            raise IndexError("Cannot pop the base repository layer")
        return super().pop()

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.pop()
        except IndexError:
            pass

    def __getattr__(self, item):
        return getattr(self.current(), item)

    def __contains__(self, item: Type):
        return any(item in repo for repo in self)


class Resolver:
    def create(
        self, factory: Callable[..., T], repository: LayeredRepository, kwargs: dict = None
    ) -> T:
        kwargs = kwargs or {}
        deps = self.get_dependencies(factory, repository, kwargs)
        deps.update(kwargs)
        return factory(**deps)

    def get_dependencies(
        self, factory: Callable[..., T], repository: LayeredRepository, kwargs: dict = None
    ) -> Dict[str, Any]:
        """Override this to """
        raise CannotResolve()


class TypeHintingResolver(Resolver):
    def get_dependencies(
        self, factory: Callable[..., T], repository: LayeredRepository, kwargs: dict = None
    ) -> Dict[str, Any]:
        kwargs = kwargs or {}
        try:
            signature = inspect.signature(factory)
        except ValueError:  # some builtin types
            raise CannotResolve()

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


class Attribute:
    name: str

    def __init__(self, cls_or_name, lazy=True):
        self.dependency = cls_or_name
        self.lazy = lazy

    def __get__(self, instance, owner):
        if instance is None:
            return self

        obj = instance.__dict__.get(self.name, EMPTY)
        if obj is EMPTY:
            obj = current_repo().get(self.dependency)
            instance.__dict__[self.name] = obj
        return obj

    def __set_name__(self, owner, name):
        self.name = name


class AttributeResolver(Resolver):
    def get_dependencies(
        self, factory: Callable[..., T], repository: LayeredRepository, kwargs: dict = None
    ) -> Dict[str, Any]:
        for attr in vars(factory).values():
            if isinstance(attr, Attribute) and not attr.lazy:
                repository.get(attr.dependency)
        raise PartiallyResolved()


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
    elif len(hint.__args__) != 1:  # just to be sure
        return None
    if collection in vars(collections.abc).values():
        collection = list

    inner_type = hint.__args__[0]
    if isinstance(inner_type, ForwardRef):
        inner_type = inner_type.__forward_arg__
    elif not isinstance(inner_type, (str, type)):
        return None

    return TypeHintInfo(collection, inner_type)


_repository = SimpleRepository(resolvers=[TypeHintingResolver()])
_repository.add(TypeHintingResolver())

# Some aliases for professional (ie. boring) people
get = that
attribute = later
