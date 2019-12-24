from collections import namedtuple
from typing import TypeVar

T = TypeVar("T")
DependencyInfo = namedtuple(
    "DependencyInfo", ["cls", "factory", "store", "kwargs"], defaults=(True, None)
)
TypeHintInfo = namedtuple("TypeHintInfo", ["collection", "inner_type"])
