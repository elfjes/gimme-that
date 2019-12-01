import dataclasses
from dataclasses import dataclass
from unittest import mock
from unittest.mock import Mock, call

import attr
import pytest

import gimme


class SimpleClass:
    ...


@gimme.dependency
class RegisteredClass:
    ...


class Dependency:
    ...


class HasDependency:
    def __init__(self, dep: Dependency):
        self.dep = dep


@attr.dataclass
class MyAttr:
    dep: Dependency
    no_init: attr.ib(init=False)
    a: int = 4
    b: list = attr.ib(factory=list)

@dataclasses.dataclass
class MyAttr:
    dep: Dependency
    no_init: dataclasses.field(init=False)
    a: int = 4
    b: list = attr.ib(factory=list)

def test_can_get_class_without_dependencies():
    assert isinstance(gimme.that(SimpleClass), SimpleClass)


def test_can_get_class_by_str_if_registered_as_dependency():
    assert isinstance(gimme.that("RegisteredClass"), RegisteredClass)


def test_can_get_class_with_requirement():
    inst = gimme.that(HasDependency)
    assert isinstance(inst, HasDependency)
    assert isinstance(inst.dep, Dependency)


@pytest.mark.xfail
def test_can_get_attrs_class():
    inst = gimme.that(MyAttr)
    assert isinstance(inst.dep, Dependency)

@pytest.mark.xfail
def test_can_get_dataclass():
    inst = gimme.that(MyAttr)
    assert isinstance(inst.dep, Dependency)

class TestRepositoryCreation:
    def test_global_repo_contains_instance_of_one(self):
        assert gimme._Repository in gimme._repository

    def test_default_repository_has_default_plugins(self):
        default_repo = gimme._repository.get(gimme._Repository)

        assert len(default_repo.plugins) == 2
        for plugin, cls in zip(
            default_repo.plugins, [gimme.TypeHintingPlugin, gimme.DefaultPlugin]
        ):
            assert isinstance(plugin, cls)

    def test_additional_plugins_are_prepended_to_default_plugins(self):
        plugin = object()
        repo = gimme._Repository(plugins=(plugin,))
        assert len(repo.plugins) == 3
        assert repo.plugins[0] is plugin

    def test_can_prevent_using_default_plugins(self):
        repo = gimme._Repository(use_default_plugins=False)
        assert len(repo.plugins) == 0


class TestRepository:
    class MyList(list):
        ...

    @pytest.fixture
    def repo(self):
        return gimme._Repository(plugins=[gimme.DefaultPlugin()], use_default_plugins=False)

    @pytest.fixture
    def dependency_info(self):
        def factory(a):
            return a

        return gimme.DependencyInfo(object, factory, {"a": 1})

    @pytest.fixture
    def failing_plugin(self):
        out = Mock()
        out.create.side_effect = gimme.CannotResolve
        return out

    def test_can_add_and_retrieve_object(self, repo):
        obj = object()
        repo.add(obj)
        assert repo.get(object) is obj

    def test_deep_add_object(self, repo):
        obj = self.MyList()
        repo.add(obj)
        assert repo.get(object) is repo.get(list) is repo.get(self.MyList) is obj

    def test_shallow_add_object(self, repo):
        obj = list()
        repo.add(obj, deep=False)
        assert list in repo
        assert object not in repo

    def test_adding_object_registers_type(self, repo):
        with mock.patch.object(repo, "register") as register:
            repo.add(object())
        assert register.call_args == call(object)

    def test_registering_adds_definitions_for_all_parents(self, repo):
        MyList = self.MyList
        repo.register(MyList)

        assert repo.types_by_str == {
            "MyList": MyList,
            "list": MyList,
            "object": MyList,
        }
        info = gimme.DependencyInfo(MyList, MyList)
        assert repo.types == {MyList: info, list: info, object: info}

    def test_can_lookup_class_by_string(self, repo):
        cls = object()
        repo.types_by_str["cls"] = cls
        with mock.patch.object(repo, "create") as create:
            repo.get("cls")

        assert create.call_args == call(cls)

    def test_raises_on_unknown_class_string(self, repo):
        with pytest.raises(gimme.CannotResolve):
            repo.get("unknown")

    def test_info_is_added_on_first_lookup(self, repo):
        repo.create(object)
        assert repo.types == {object: gimme.DependencyInfo(object, object)}

    def test_can_register_with_alternative_factory(self, repo, dependency_info):
        repo.register(dependency_info.cls, dependency_info.factory, dependency_info.kwargs)
        assert repo.types[object] == dependency_info

    def test_create_calls_plugin_with_factory_and_kwargs(self, repo, dependency_info):
        plugin = Mock()
        repo.plugins = [plugin]
        repo.types[object] = dependency_info
        repo.create(object)
        assert plugin.create.call_args == call(
            dependency_info.factory, repo, dependency_info.kwargs
        )

    def test_create_moves_to_next_plugin_on_CannotResolve(
        self, repo, dependency_info, failing_plugin
    ):
        repo.plugins = [failing_plugin, Mock()]
        repo.types[object] = dependency_info
        repo.create(object)
        for plugin in repo.plugins:
            assert plugin.create.call_args == call(
                dependency_info.factory, repo, dependency_info.kwargs
            )

    def test_raises_when_no_plugin_can_resolve_dependency(self, repo, failing_plugin):
        repo.plugins = [failing_plugin, failing_plugin]
        with pytest.raises(gimme.CannotResolve) as e:
            repo.get(object)
        assert str(e.value) == str(object)
