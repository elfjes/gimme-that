from __future__ import annotations

import inspect
import typing as t

from gimme.attribute import Attribute
from gimme.exceptions import CannotResolve, PartiallyResolved
from gimme.helpers import is_generic_type_hint, parse_type_hint
from gimme.types import T, CollectionTypeHintInfo

if t.TYPE_CHECKING:
    from gimme.repository import LayeredRepository


class Resolver:
    """Base class for creating extensions to the dependency resolution system. Subclass this class
    and add instances of your class to the repository using :func:`gimme.add_resolver` or
    :func:`gimme.setup`
    """

    def create(
        self,
        factory: t.Callable,
        repository: LayeredRepository,
        kwargs: dict = None,
    ) -> T:
        kwargs = kwargs or {}
        deps = self.get_dependencies(factory, repository, kwargs)
        deps.update(kwargs)
        return factory(**deps)

    def get_dependencies(
        self,
        factory: t.Callable,
        repository: LayeredRepository,
        kwargs: dict = None,
    ) -> t.Dict[str, t.Any]:
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
        factory: t.Callable,
        repository: LayeredRepository,
        kwargs: dict = None,
    ) -> t.Dict[str, t.Any]:
        kwargs = kwargs or {}
        try:
            signature = inspect.signature(factory)
        except ValueError:  # some builtin types
            raise CannotResolve()

        try:
            type_hints = self.get_type_hints(factory, repository)
        except NameError as e:
            raise CannotResolve() from e

        # The signature of a callable may differ from its type annotations, for example when
        # __new__ has been overridden with (*args, **kwargs), `inspect.signature` can then
        # not properly determine the signature. We have to make sure resolve any
        # non-variadic arguments that have no default value, as well as all parameters in
        # __annotations__ for arguments that do not have a default value

        nonvariadic_params = {
            name
            for name, param in signature.parameters.items()
            if param.kind not in (param.VAR_KEYWORD, param.VAR_POSITIONAL)
        }
        variadic_params = {
            name
            for name, param in signature.parameters.items()
            if param.kind in (param.VAR_KEYWORD, param.VAR_POSITIONAL)
        }
        default_params = {
            name
            for name, param in signature.parameters.items()
            if param.default is not param.empty
        }
        all_required = (
            (nonvariadic_params | set(type_hints.keys()))
            - variadic_params
            - default_params
            - set(kwargs.keys())
            - {"return"}  # return is a special annotation indiciting the return type
        )

        dependencies = {}

        for key in all_required:

            try:
                annotation = type_hints[key]
            except KeyError as e:
                raise CannotResolve(key) from e

            if is_generic_type_hint(annotation):
                result = parse_type_hint(annotation)
                if isinstance(result, CollectionTypeHintInfo):
                    dependencies[key] = result.collection(
                        repository.get(result.inner_type, many=True)
                    )
                    continue
                elif result is not None:
                    annotation = result
                else:
                    raise CannotResolve(key, annotation)
            dependencies[key] = repository.get(annotation)
        return dependencies

    @staticmethod
    def get_type_hints(obj, repository: LayeredRepository):
        if isinstance(obj, type):
            obj = obj.__init__

        return t.get_type_hints(obj, localns=repository.types_by_str)


class AttributeResolver(Resolver):
    def get_dependencies(
        self,
        factory: t.Callable,
        repository: LayeredRepository,
        kwargs: dict = None,
    ) -> t.Dict[str, t.Any]:
        for attr in vars(factory).values():
            if isinstance(attr, Attribute) and not attr.lazy:
                repository.get(attr.dependency)
        raise PartiallyResolved()
