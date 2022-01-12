from __future__ import annotations
from gimme.helpers import EMPTY
import typing as t

if t.TYPE_CHECKING:
    from gimme.repository import LayeredRepository


class Attribute:
    name: str

    def __init__(self, cls_or_name, repo: LayeredRepository, lazy=True):
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
