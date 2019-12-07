import dataclasses
from dataclasses import dataclass
from typing import List, Sequence, Iterable, Set, Dict, Tuple, NamedTuple
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
    no_init: int = attr.ib(init=False)
    a: int = 4
    b: list = attr.ib(factory=list)


@dataclasses.dataclass
class MyAttr:
    dep: Dependency
    no_init: int = dataclasses.field(init=False)
    a: int = 4
    b: list = attr.ib(factory=list)


@pytest.fixture
def repo():
    return gimme._Repository(plugins=[gimme.DefaultResolver()])


def test_can_get_class_without_dependencies():
    assert isinstance(gimme.that(SimpleClass), SimpleClass)


def test_can_get_class_by_str_if_registered_as_dependency():
    assert isinstance(gimme.that("RegisteredClass"), RegisteredClass)


def test_can_get_class_with_requirement():
    inst = gimme.that(HasDependency)
    assert isinstance(inst, HasDependency)
    assert isinstance(inst.dep, Dependency)


def test_can_get_attrs_class():
    inst = gimme.that(MyAttr)
    assert isinstance(inst.dep, Dependency)


def test_can_get_dataclass():
    inst = gimme.that(MyAttr)
    assert isinstance(inst.dep, Dependency)


def test_base_plugin_cant_resolve():
    plugin = gimme.Resolver()
    with pytest.raises(gimme.CannotResolve):
        plugin.create(object, Mock())


class TestRepositorySetup:
    def test_global_repo_contains_instance_of_one(self):
        assert gimme._Repository in gimme._repository

    def test_default_repository_has_default_resolvers(self):
        default_repo = gimme._repository.get(gimme._Repository)

        resolver_types = [type(res) for res in default_repo.resolvers]
        assert resolver_types == [gimme.TypeHintingResolver]

    def test_can_add_resolvers(self):
        default_repo = gimme.current_repo()
        curr_len = len(default_repo.resolvers)
        obj = object()
        default_repo.add_resolver(obj)
        assert default_repo.resolvers[0] is obj
        assert len(default_repo.resolvers) == 1 + curr_len
        default_repo.resolvers.remove(obj)


class TestRepository:
    class MyList(list):
        ...

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
            "list": list,
            "object": object,
        }
        info = gimme.DependencyInfo(MyList, MyList)
        assert repo.types == {MyList: info, list: info, object: info}

    def test_can_lookup_obj_by_string(self, repo):
        obj = object()
        repo.add(obj)

        assert repo.get("object") is obj

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
        repo.resolvers = [plugin]
        repo.types[object] = dependency_info
        repo.create(object)
        assert plugin.create.call_args == call(
            dependency_info.factory, repo, dependency_info.kwargs
        )

    def test_create_moves_to_next_plugin_on_CannotResolve(
        self, repo, dependency_info, failing_plugin
    ):
        repo.resolvers = [failing_plugin, Mock()]
        repo.types[object] = dependency_info
        repo.create(object)
        for plugin in repo.resolvers:
            assert plugin.create.call_args == call(
                dependency_info.factory, repo, dependency_info.kwargs
            )

    def test_raises_when_no_plugin_can_resolve_dependency(self, repo, failing_plugin):
        repo.resolvers = [failing_plugin, failing_plugin]
        with pytest.raises(gimme.CannotResolve) as e:
            repo.get(object)
        assert str(e.value) == str(object)


class TestWhenMultipleHaveBeenRegistered:
    def test_can_get_multiple_when_multiple_have_been_added(self, repo):
        repo.add(SimpleClass())
        repo.add(SimpleClass())

        instances = repo.get(SimpleClass, many=True)
        assert isinstance(instances, list)
        assert len(instances) == 2

    def test_get_latest_when_asking_for_one(self, repo):
        a = SimpleClass()
        repo.add(SimpleClass())
        repo.add(a)
        assert repo.get(SimpleClass, many=False) is a

    def test_can_get_multiple_derived_instances(self, repo):
        class Base:
            ...

        class DerivedA(Base):
            ...

        class DerivedB(Base):
            ...

        repo.add(DerivedA())
        repo.add(DerivedB())

        instances = repo.get(Base, many=True)
        assert isinstance(instances, list)
        assert len(instances) == 2
        for inst, cls in zip(instances, [DerivedA, DerivedB]):
            assert isinstance(inst, cls)


def test_circular_dependencies(repo):
    class A:
        def __init__(self, c: "C"):
            ...

    class B:
        def __init__(self, a: A):
            ...

    @repo.register
    class C:
        def __init__(self, b: B):
            ...

    repo.add_resolver(gimme.TypeHintingResolver())
    with pytest.raises(gimme.CircularDependeny) as err:
        repo.get(A)
    assert str(err.value) == "A -> C -> B"


def test_lookup_stack_is_cleared_after_successful_get(repo):
    repo.get(SimpleClass)
    assert not repo.lookup_stack


def test_lookup_stack_is_cleared_after_unsucessful_get(repo):
    with pytest.raises(gimme.CannotResolve):
        repo.get("Invalid")
    assert not repo.lookup_stack


@pytest.mark.parametrize(
    "hint,expected",
    [
        (List[int], list),
        (Sequence[int], list),
        (Iterable[int], list),
        (Set[int], set),
        (List, None),
        (Dict[int, int], None),
        (List[List[int]], None),
        (Tuple[int, ...], tuple),
        (Tuple[int, int], None),
        (list, None),
        (NamedTuple("Tuple", [("field", int)]), None),
    ],
)
def test_can_parse_collection(hint, expected):
    result = gimme.parse_collection_from_type_hint(hint)
    if expected is not None:
        result = result.collection

    assert result is expected
