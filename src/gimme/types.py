from typing import TypeVar, NamedTuple, Callable, Optional

T = TypeVar("T")


class DependencyInfo(NamedTuple):
    cls: type
    factory: Callable
    store: bool = True
    kwargs: Optional[dict] = None


class CollectionTypeHintInfo(NamedTuple):
    collection: type
    inner_type: type
