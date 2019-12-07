from typing import Tuple
from unittest import mock
from unittest.mock import Mock, call

import pytest

from gimme import TypeHintingResolver, CannotResolve


@pytest.fixture
def plugin():
    return TypeHintingResolver()


def test_can_create_with_deps_and_kwargs(plugin):
    class MyClass:
        def __init__(self, a, b):
            self.a = a
            self.b = b

    with mock.patch.object(plugin, "get_dependencies", return_value={"a": 1}):
        obj = plugin.create(MyClass, None, {"b": 2})
    assert (obj.a, obj.b) == (1, 2)


def test_no_dependencies_for_class_without_dependencies(plugin):
    class ClassWithoutDependencies:
        pass

    repo = Mock()
    assert not plugin.get_dependencies(ClassWithoutDependencies, repo).keys()

    assert repo.get.call_count == 0


def test_get_dependencies_for_class_with_dependencies(plugin):
    class ClassWithDependencies:
        def __init__(self, a: int, b: str, c=None, d: list = None):
            pass

    repo = Mock()
    assert plugin.get_dependencies(ClassWithDependencies, repo).keys() == {"a", "b"}

    assert repo.get.call_args_list == [call(int), call(str)]


def test_dont_resolve_dependency_that_is_also_in_kwargs(plugin):
    class ClassWithDependencies:
        def __init__(self, a: int, b: str):
            pass

    repo = Mock()
    deps = plugin.get_dependencies(ClassWithDependencies, repo, kwargs={"b": "value"})
    assert deps.keys() == {"a"}

    assert repo.get.call_args_list == [call(int)]


def test_raises_on_unresolvable_class(plugin):
    class UnresolvableClass:
        def __init__(self, a: int, b):
            pass

    repo = Mock()
    with pytest.raises(CannotResolve):
        assert plugin.get_dependencies(UnresolvableClass, repo)


def test_get_dependencies_for_function(plugin):
    def function(a: int, b: str, c: list = None, *, d: set, e: tuple = ()):
        pass

    repo = Mock()
    assert plugin.get_dependencies(function, repo).keys() == {"a", "b", "d"}
    assert repo.get.call_args_list == [call(int), call(str), call(set)]


def test_get_dependencies_with_generic_type(plugin):
    def function(a: Tuple[int, ...]):
        pass

    repo = Mock()
    repo.get.return_value = [1, 2]
    assert plugin.get_dependencies(function, repo) == {"a": (1, 2)}
    assert repo.get.call_args_list == [call(int, many=True)]
