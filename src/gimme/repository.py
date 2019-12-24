from itertools import chain
from typing import Iterable, List, Dict, Type, Union, Callable, TYPE_CHECKING

from .exceptions import CannotResolve, CircularDependency, PartiallyResolved
from .helpers import _Stack, _LookupStack, EMPTY
from .types import T, DependencyInfo

if TYPE_CHECKING:
    from .resolvers import Resolver


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


class LayeredRepository(_Stack):
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


class Attribute:
    name: str

    def __init__(self, cls_or_name, repo: "LayeredRepository", lazy=True):
        self.dependency = cls_or_name
        self.lazy = lazy
        self.repo = repo

    def __get__(self, instance, owner):
        if instance is None:
            return self

        obj = instance.__dict__.get(self.name, EMPTY)
        if obj is EMPTY:
            obj = self.repo.get(self.dependency)
            instance.__dict__[self.name] = obj
        return obj

    def __set_name__(self, owner, name):
        self.name = name
