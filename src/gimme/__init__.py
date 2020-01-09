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
    that,
    register,
    setup,
)
from .repository import LayeredRepository, SimpleRepository
from .resolvers import AttributeResolver, TypeHintingResolver

__version__ = "0.1.3"

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
]
