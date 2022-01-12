from __future__ import annotations

from itertools import chain
import typing as t

from .exceptions import CannotResolve, CircularDependency, PartiallyResolved
from .helpers import EMPTY, _LookupStack, _Stack
from .types import DependencyInfo, T

from .resolvers import Resolver


class SimpleRepository:
    def __init__(self, resolvers: t.Iterable[Resolver]):

        self.resolvers: t.List[Resolver] = list(resolvers)
        self.types_by_str: t.Dict[str, t.Type[T]] = {}
        self.types: t.Dict[t.Type, DependencyInfo] = {}
        self.instances: t.Dict[t.Type[T], t.List[T]] = {}
        self.lookup_stack = _LookupStack()

    def get(
        self, key: t.Union[t.Type[T], str], many=False, repo=None, kwargs=None
    ) -> t.Union[t.List[T], T]:
        if isinstance(key, str):
            key = self.types_by_str.get(key)
        if key is None:
            raise CannotResolve(f"Could not resolve for key {key}")

        if many:
            return self.instances.get(key, [])

        if not isinstance(key, type) and callable(key):
            name = getattr(key, "__name__", str(key))
            return self.resolve(factory=key, key=name, repo=repo, kwargs=kwargs)

        if kwargs is not None or key not in self.instances:
            inst = self.create(key, repo=repo, kwargs=kwargs)
            return inst

        instances = self.instances[key]
        return instances[-1]

    def create(self, key: t.Type[T], repo=None, kwargs=None) -> T:
        """Instantiate the object and all its dependencies
        :param key: The class / factory function to instantiate
        :param repo: The current ``Repository`` used for requesting dependencies
        :param kwargs: Any user specified keyword arguments (see :func:`gimme.get`). These
            will have preference over any keyword arguments this function supplies and any
            keyword arguments supplied by :func:`gimme.register`

        """
        repo = repo or self
        if not isinstance(key, type):
            raise TypeError(f"Can only create classes, not {key}")
        if key in self.lookup_stack:
            raise CircularDependency(str(self.lookup_stack))
        info = self._ensure_info(key)
        do_store = kwargs is None and info.store
        if kwargs is not None:
            kwargs = {**(info.kwargs or {}), **kwargs}
        inst = self.resolve(info.factory, key=key, repo=repo, kwargs=kwargs)
        if do_store:
            self.add(inst)
        return inst

    def resolve(self, factory, key, repo=None, kwargs=None):
        """Resolve a factory function. This resolves all function parameters as dependencies,
        runs the function and returns the result
        """
        inst = EMPTY
        with self.lookup_stack.push(key):
            for plugin in self.resolvers:
                try:
                    return plugin.create(factory, repo, kwargs)
                except (CannotResolve, PartiallyResolved):
                    continue
            if inst is EMPTY:
                raise CannotResolve(str(self.lookup_stack))

    def _ensure_info(self, cls: t.Type[T]) -> DependencyInfo:
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
        cls: t.Type[T] = None,
        factory: t.Callable = None,
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

    def add_resolver(self, resolver: Resolver):
        self.resolvers.insert(0, resolver)

    def __contains__(self, item: t.Type):
        return item in self.instances


class LayeredRepository(_Stack[SimpleRepository]):
    def __init__(self, first_layer: SimpleRepository):
        super().__init__([first_layer])

    @property
    def current(self) -> SimpleRepository:
        return self[-1]

    def get(self, key: t.Union[t.Type[T], str], many=False, kwargs=None) -> t.Union[t.List[T], T]:
        err = None

        if many:
            return list(chain.from_iterable(repo.get(key, many) for repo in self))

        for repo in reversed(self):
            try:
                return repo.get(key, many, repo=self, kwargs=kwargs)
            except CannotResolve as e:
                err = e
        if err:
            raise err

    def create(self, key: t.Type[T]) -> T:
        return self.current.create(key, repo=self)

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
        return getattr(self.current, item)

    def __contains__(self, item: t.Type):
        return any(item in repo for repo in self)
