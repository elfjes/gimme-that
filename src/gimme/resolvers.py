import inspect
from typing import Callable, Dict, Any, TYPE_CHECKING

from gimme.helpers import parse_type_hint
from gimme.types import T
from gimme.exceptions import CannotResolve, PartiallyResolved
from gimme.repository import Attribute

if TYPE_CHECKING:
    from gimme.repository import LayeredRepository


class Resolver:
    def create(
        self, factory: Callable[..., T], repository: "LayeredRepository", kwargs: dict = None
    ) -> T:
        kwargs = kwargs or {}
        deps = self.get_dependencies(factory, repository, kwargs)
        deps.update(kwargs)
        return factory(**deps)

    def get_dependencies(
        self, factory: Callable[..., T], repository: "LayeredRepository", kwargs: dict = None
    ) -> Dict[str, Any]:
        """Override this to """
        raise CannotResolve()


class TypeHintingResolver(Resolver):
    def get_dependencies(
        self, factory: Callable[..., T], repository: "LayeredRepository", kwargs: dict = None
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
        self, factory: Callable[..., T], repository: "LayeredRepository", kwargs: dict = None
    ) -> Dict[str, Any]:
        for attr in vars(factory).values():
            if isinstance(attr, Attribute) and not attr.lazy:
                repository.get(attr.dependency)
        raise PartiallyResolved()
