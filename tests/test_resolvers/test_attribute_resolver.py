from unittest.mock import Mock, call

import pytest

import gimme


@pytest.fixture
def resolver():
    return gimme.AttributeResolver()


@pytest.fixture
def repo():
    return Mock()


def test_can_resolve_attributes(resolver, repo):
    class MyClass:
        dep = gimme.Attribute(int, lazy=False)

    with pytest.raises(gimme.PartiallyResolved):
        resolver.get_dependencies(MyClass, repo)

    assert repo.get.call_args == call(int)


def test_lazy_default_doesnt_resolve_immediately(resolver, repo):
    class MyClass:
        dep = gimme.Attribute(int)

    with pytest.raises(gimme.PartiallyResolved):
        resolver.get_dependencies(MyClass, repo)

    assert repo.get.call_count == 0
