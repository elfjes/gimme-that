import collections
from typing import Optional, ForwardRef

from .types import TypeHintInfo


def is_generic_type_hint(hint):
    return hasattr(hint, "__origin__")


def parse_type_hint(hint) -> Optional[TypeHintInfo]:
    """
    Get the constructor for iterable/sequence type hints:
    returns the concrete type belonging to the type hint, ie `set` for `typing.Set`
    for the abstract type hints typing.Iterable
    :param hint: A Generic Type hint
    :returns: TypeHintInfo, or None if it could not be parsed into a list-like collection of
    `type`. eg for nested generic types (`List[List[int]]`)
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


class _Stack(list):
    def push(self, item):
        self.append(item)
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.pop()


class _LookupStack(_Stack):
    def __str__(self):
        return " -> ".join(getattr(i, "__name__", str(i)) for i in self)


EMPTY = object()