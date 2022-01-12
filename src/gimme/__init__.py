from .main import (
    add,
    add_resolver,
    attribute,
    context,
    current_repo,
    dependency,
    get,
    later,
    pop_context,
    register,
    setup,
    that,
)
from .repository import LayeredRepository, SimpleRepository
from .resolvers import AttributeResolver, TypeHintingResolver
from .types import DependencyInfo

__version__ = "0.2.1"

__all__ = [
    "add",
    "add_resolver",
    "attribute",
    "context",
    "current_repo",
    "dependency",
    "get",
    "later",
    "pop_context",
    "register",
    "setup",
    "that",
    "LayeredRepository",
    "SimpleRepository",
    "AttributeResolver",
    "TypeHintingResolver",
    "DependencyInfo",
]
