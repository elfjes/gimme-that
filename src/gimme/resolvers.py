import inspect
from typing import Callable, Dict, Any

import gimme.repository
from gimme.exceptions import CannotResolve, PartiallyResolved
from gimme.helpers import parse_type_hint
from gimme.repository import Attribute
from gimme.types import T


class Resolver:
    """Base class for creating extensions to the dependency resolution system. Subclass this class
    and add instances of your class to the repository using :func:`gimme.add_resolver` or
    :func:`gimme.setup`
    """

    def create(
        self,
        factory: Callable,
        repository: gimme.repository.LayeredRepository,
        kwargs: dict = None,
    ) -> T:
        kwargs = kwargs or {}
        deps = self.get_dependencies(factory, repository, kwargs)
        deps.update(kwargs)
        return factory(**deps)

    def get_dependencies(
        self,
        factory: Callable,
        repository: gimme.repository.LayeredRepository,
        kwargs: dict = None,
    ) -> Dict[str, Any]:
        """Override this to customize how to resolve the dependencies of a specific class /
        factory function. This method will be called with the following arguments:

        :param factory: The class / factory function to determine the dependencies for
        :param repository: The current ``Repository`` can be used for requesting dependencies
        :param kwargs: Any user specified keyword arguments (see :func:`gimme.register`). These
            will have preference over any keyword arguments this function supplies

        Your ``Resolver`` may do one of three things:

        * Return a dictionary of keyword arguments to supply to the factory upon instantiation
        * Raise :exc:`~gimme.exceptions.CannotResolve` if your ``Resolver`` cannot return an
          instantiated object and the next ``Resolver`` should be tried
        * Raise :exc:`~gimme.exceptions.PartiallyResolved` if your ``Resolver`` did resolve some,
          but not all of the dependencies
        """
        raise CannotResolve()


class TypeHintingResolver(Resolver):
    def get_dependencies(
        self,
        factory: Callable,
        repository: gimme.repository.LayeredRepository,
        kwargs: dict = None,
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
                info = parse_type_hint(annotation)
                if info:
                    dependencies[key] = info.collection(repository.get(info.inner_type, many=True))
                    continue
                else:
                    raise CannotResolve(key, param.annotation)
            dependencies[key] = repository.get(param.annotation)
        return dependencies


class AttributeResolver(Resolver):
    def get_dependencies(
        self,
        factory: Callable,
        repository: gimme.repository.LayeredRepository,
        kwargs: dict = None,
    ) -> Dict[str, Any]:
        for attr in vars(factory).values():
            if isinstance(attr, Attribute) and not attr.lazy:
                repository.get(attr.dependency)
        raise PartiallyResolved()
