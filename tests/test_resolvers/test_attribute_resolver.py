from unittest.mock import Mock, call

import pytest

import gimme
from gimme.exceptions import PartiallyResolved
import gimme.resolvers


@pytest.fixture
def resolver():
    return gimme.resolvers.AttributeResolver()


@pytest.fixture
def repo():
    return Mock()


def test_can_resolve_attributes(resolver, repo):
    class MyClass:
        dep = gimme.Attribute(int, lazy=False, repo=repo)

    with pytest.raises(PartiallyResolved):
        resolver.get_dependencies(MyClass, repo)

    assert repo.get.call_args == call(int)


def test_lazy_default_doesnt_resolve_immediately(resolver, repo):
    class MyClass:
        dep = gimme.Attribute(int, repo=repo)

    with pytest.raises(PartiallyResolved):
        resolver.get_dependencies(MyClass, repo)

    assert repo.get.call_count == 0
