import typing as t
from unittest import mock
from unittest.mock import Mock, call

import pytest

from gimme.exceptions import CannotResolve
from gimme.resolvers import TypeHintingResolver


@pytest.fixture
def plugin():
    return TypeHintingResolver()


@pytest.fixture
def repo():
    repo = Mock()
    repo.types_by_str = {}
    return repo


def test_can_create_with_deps_and_kwargs(plugin):
    class MyClass:
        def __init__(self, a, b):
            self.a = a
            self.b = b

    with mock.patch.object(plugin, "get_dependencies", return_value={"a": 1}):
        obj = plugin.create(MyClass, None, {"b": 2})
    assert (obj.a, obj.b) == (1, 2)


def test_no_dependencies_for_class_without_dependencies(plugin, repo):
    class ClassWithoutDependencies:
        pass

    assert not plugin.get_dependencies(ClassWithoutDependencies, repo).keys()

    assert repo.get.call_count == 0


def test_get_dependencies_for_class_with_dependencies(plugin, repo):
    class ClassWithDependencies:
        def __init__(self, a: int, b: str, c=None, d: list = None):
            pass

    assert plugin.get_dependencies(ClassWithDependencies, repo).keys() == {"a", "b"}

    assert {call_args[0][0] for call_args in repo.get.call_args_list} == {int, str}


def test_dont_resolve_dependency_that_is_also_in_kwargs(plugin, repo):
    class ClassWithDependencies:
        def __init__(self, a: int, b: str):
            pass

    deps = plugin.get_dependencies(ClassWithDependencies, repo, kwargs={"b": "value"})
    assert deps.keys() == {"a"}

    assert repo.get.call_args_list == [call(int)]


def test_raises_on_unresolvable_class(plugin, repo):
    class UnresolvableClass:
        def __init__(self, a: int, b):
            pass

    with pytest.raises(CannotResolve):
        assert plugin.get_dependencies(UnresolvableClass, repo)


def test_get_dependencies_for_function(plugin, repo):
    def function(a: int, b: str, c: list = None, *, d: set, e: tuple = ()):
        pass

    assert plugin.get_dependencies(function, repo).keys() == {"a", "b", "d"}
    assert {call_args[0][0] for call_args in repo.get.call_args_list} == {int, str, set}


def test_get_dependencies_with_generic_type(plugin, repo):
    def function(a: t.Tuple[int, ...]):
        pass

    repo.get.return_value = [1, 2]
    assert plugin.get_dependencies(function, repo) == {"a": (1, 2)}
    assert repo.get.call_args_list == [call(int, many=True)]


def test_cannot_resolve_invalid_type_hint(plugin, repo):
    def function(a: t.Tuple[int, int]):
        pass

    with pytest.raises(CannotResolve):
        plugin.get_dependencies(function, repo)


@pytest.mark.parametrize("tp", [int, str, dict])
def test_raise_cannot_resolve_on_unresolvable_builtin_types(plugin, repo, tp):
    with pytest.raises(CannotResolve):
        plugin.get_dependencies(tp, repo)


def test_ignores_variadic_positional_arguments(plugin, repo):
    def func(*args):
        return 42

    assert plugin.get_dependencies(func, repo) == {}


def test_ignores_variadic_keyword_arguments(plugin, repo):
    def func(**kwargs):
        return 42

    assert plugin.get_dependencies(func, repo) == {}


def test_with_overridden_new(plugin, repo):
    class MyClass:
        def __new__(cls, *args, **kwargs):
            return object.__new__(cls)

        def __init__(self, dep: int) -> None:
            self.dep = dep

    plugin.get_dependencies(MyClass, repo)
    assert repo.get.call_args == call(int)


def test_with_annotated_variadic_arguments(plugin, repo):
    class MyClass:
        def __init__(self, a: int, *args: t.Any, **kwargs: t.Any) -> None:
            pass

    plugin.get_dependencies(MyClass, repo)
    assert repo.get.call_count == 1
    assert repo.get.call_args == call(int)
