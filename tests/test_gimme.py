from typing import Dict, Iterable, List, NamedTuple, Sequence, Set, Tuple
from unittest import mock
from unittest.mock import Mock, call
import sys

import attr
import gimme
import gimme.exceptions
import gimme.helpers
import gimme.repository
import gimme.resolvers
import gimme.types
import pytest
import typing as t


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


@pytest.fixture(autouse=True)
def repo():
    with gimme.context() as repo:
        yield repo


def test_can_get_class_without_dependencies():
    assert isinstance(gimme.that(SimpleClass), SimpleClass)


def test_can_get_class_by_str_if_registered_as_dependency():
    assert isinstance(gimme.that("RegisteredClass"), RegisteredClass)


def test_can_get_class_with_requirement():
    inst = gimme.that(HasDependency)
    assert isinstance(inst, HasDependency)
    assert isinstance(inst.dep, Dependency)


def test_stores_by_default():
    assert gimme.get(HasDependency) is gimme.get(HasDependency)


def test_can_get_attrs_class():
    @attr.dataclass
    class MyAttr:
        dep: Dependency
        no_init: int = attr.ib(init=False)
        a: int = 4
        b: list = attr.ib(factory=list)

    inst = gimme.that(MyAttr)
    assert isinstance(inst.dep, Dependency)


@pytest.mark.skipif(sys.version_info < (3, 7), reason="no dataclasses in py3.6")
def test_can_get_dataclass():
    import dataclasses

    @dataclasses.dataclass
    class MyDataclass:
        dep: Dependency
        no_init: int = dataclasses.field(init=False)
        a: int = 4
        b: list = attr.ib(factory=list)

    inst = gimme.that(MyDataclass)
    assert isinstance(inst.dep, Dependency)


def test_base_plugin_cant_resolve():
    plugin = gimme.resolvers.Resolver()
    with pytest.raises(gimme.exceptions.CannotResolve):
        plugin.create(object, Mock())


class TestRepositorySetup:
    def test_global_repo_contains_instance_of_one(self):
        assert gimme.LayeredRepository in gimme.main._repository

    def test_default_repository_has_default_resolvers(self):
        default_repo = gimme.main._repository.get(gimme.LayeredRepository)

        resolver_types = [type(res) for res in default_repo.resolvers]
        assert resolver_types == [gimme.TypeHintingResolver]

    def test_can_add_resolvers(self, repo):
        curr_len = len(repo.resolvers)
        obj = object()
        repo.add_resolver(obj)
        assert repo.resolvers[0] is obj
        assert len(repo.resolvers) == 1 + curr_len

    def test_global_setup(self, repo):
        objs = list(), 15
        types = str, gimme.types.DependencyInfo(dict, dict)
        resolver = object()
        gimme.setup(objects=objs, types=types, resolvers=[resolver])

        assert repo.resolvers[0] == resolver
        for tp in str, dict:
            assert tp in repo.types
        for tp in list, int:
            assert tp in repo.instances


class TestSupplyKwargsOnGet:
    @pytest.fixture
    def cls(self):
        class MyClass:
            def __init__(self, dep: Dependency, other_dep: Dependency) -> None:
                self.dep = dep
                self.other_dep = other_dep

        return MyClass

    def test_can_supply_kwargs_on_get(self, cls):
        other_dep = object()
        inst = gimme.that(cls, other_dep=other_dep)
        assert isinstance(inst.dep, Dependency)
        assert inst.other_dep is other_dep

    def test_always_creates_new_object_when_supplying_kwargs(self, cls):
        other_dep = object()
        assert gimme.that(cls) is not gimme.that(cls, other_dep=other_dep)

    def test_doesnt_store_object_when_supplying_kwargs(
        self, cls, repo: gimme.repository.SimpleRepository
    ):
        other_dep = object()
        gimme.that(cls, other_dep=other_dep)
        assert cls not in repo


class TestResolveFunction:
    def test_resolve_type_annotated_factory_function(self):
        def factory(a: Dependency):
            return dict(a=a)

        result = gimme.that(factory)
        assert isinstance(result["a"], Dependency)

    def test_pretty_error_on_failure(self):
        def failing(invalid):
            pass

        with pytest.raises(gimme.exceptions.CannotResolve) as exc:
            gimme.that(failing)
        assert "failing" in str(exc.value)

    def test_doenst_store_result(self, repo):
        def factory():
            return 42

        gimme.that(factory)
        assert not repo.instances

    def test_stores_dependenies(self, repo):
        def factory(a: Dependency):
            return 42

        assert Dependency not in repo

        gimme.that(factory)
        assert Dependency in repo

    def test_takes_kwargs(self):
        def factory(a):
            return dict(a=a)

        result = gimme.that(factory, a=42)
        assert result["a"] == 42


class TestRepository:
    class MyList(list):
        ...

    @pytest.fixture
    def dependency_info(self):
        def factory(a):
            return a

        return gimme.types.DependencyInfo(object, factory, kwargs={"a": 1})

    @pytest.fixture
    def failing_plugin(self):
        out = Mock()
        out.create.side_effect = gimme.exceptions.CannotResolve
        return out

    def test_can_add_and_retrieve_object(self, repo):
        obj = object()
        gimme.add(obj)
        assert gimme.that(object) is obj

    def test_deep_add_object(self, repo):
        obj = self.MyList()
        repo.add(obj)
        assert repo.get(object) is repo.get(list) is repo.get(self.MyList) is obj

    def test_shallow_add_object(self, repo):
        class MyList(list):
            ...

        obj = MyList()
        repo.add(obj, deep=False)
        assert MyList in repo
        assert list not in repo

    def test_adding_object_registers_type(self, repo):
        class NewType:
            ...

        with mock.patch.object(repo.current, "register") as register:
            repo.add(NewType())
        assert register.call_args == call(NewType)

    def test_registering_adds_definitions_for_all_parents(self, repo):
        MyList = self.MyList
        repo.register(MyList)

        assert repo.types_by_str == {"MyList": MyList, "list": list, "object": object}
        info = gimme.types.DependencyInfo(MyList, MyList)
        assert repo.types == {MyList: info, list: info, object: info}

    def test_can_add_for_different_type(self, repo):
        class MyType:
            pass

        sentinel = object()
        repo.add(sentinel, cls=MyType)
        assert repo.get(MyType) is sentinel

    def test_can_register_with_factory_function_for_different_type(self, repo):
        class MyType:
            pass

        class MyDummy:
            pass

        repo.register(MyType, factory=MyDummy)
        repo.create(MyType)
        assert MyType in repo

    def test_can_lookup_obj_by_string(self, repo):
        obj = object()
        repo.add(obj)

        assert repo.get("object") is obj

    def test_raises_on_unknown_class_string(self, repo):
        with pytest.raises(gimme.exceptions.CannotResolve):
            repo.get("unknown")

    def test_info_is_added_on_first_lookup(self, repo):
        repo.create(SimpleClass)
        assert repo.types[SimpleClass] == gimme.types.DependencyInfo(SimpleClass, SimpleClass)

    def test_can_register_with_alternative_factory(self, repo, dependency_info):
        repo.register(info=dependency_info)
        assert repo.types[object] == dependency_info

    def test_create_calls_plugin_with_factory_and_kwargs(self, repo, dependency_info):
        plugin = Mock()
        layer = repo.current
        layer.resolvers = [plugin]
        layer.types[object] = dependency_info
        layer.create(object)
        assert plugin.create.call_args == call(
            dependency_info.factory, layer, dependency_info.kwargs
        )

    def test_create_moves_to_next_plugin_on_CannotResolve(
        self, repo, dependency_info, failing_plugin
    ):
        layer = repo.current
        layer.resolvers = [failing_plugin, Mock()]
        layer.types[object] = dependency_info
        layer.create(object)
        for plugin in repo.resolvers:
            assert plugin.create.call_args == call(
                dependency_info.factory, layer, dependency_info.kwargs
            )

    def test_raises_when_no_plugin_can_resolve_dependency(self, repo, failing_plugin):
        repo = gimme.repository.SimpleRepository([failing_plugin, failing_plugin])
        with pytest.raises(gimme.exceptions.CannotResolve) as e:
            repo.get(object)
        assert str(e.value) == "object"

    def test_gets_multiple_instances_when_not_storing(self, repo):
        repo.register(SimpleClass, store=False)
        assert repo.get(SimpleClass) is not repo.get(SimpleClass)

    def test_generic_class(self, repo):
        T = t.TypeVar("T")

        class SomeGeneric(t.Generic[T]):
            def __init__(self) -> None:
                ...

        class Depends(t.Generic[T]):
            def __init__(self, generic: SomeGeneric[T]) -> None:
                self.generic = generic

        result = repo.get(Depends)
        assert isinstance(result.generic, SomeGeneric)


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


class TestContext:
    def test_can_context_dependent_dependency(self):
        gimme.add(2)
        with gimme.context():
            gimme.add(1)
            assert gimme.that(int) == 1
        assert gimme.that(int) == 2

    def test_can_get_many(self, repo):
        repo.add(1)
        repo.add(2)
        assert repo.get(int, many=True) == [1, 2]

    def test_manual_pushing_and_popping_contexts(self):
        gimme.add(2)
        gimme.context()

        gimme.add(1)
        assert gimme.that(int) == 1
        gimme.pop_context()

        assert gimme.that(int) == 2

    def test_resolve_from_multiple_layers(self):
        class MyClass:
            def __init__(self, a: int, b: str):
                self.a = a
                self.b = b

        gimme.add(2)
        with gimme.context():
            gimme.add("bla")
            obj = gimme.that(MyClass)
        assert (obj.a, obj.b) == (2, "bla")

    def test_get_from_lower_layer(self):
        class MyClass:
            def __init__(self, a=None) -> None:
                self.a = a

        gimme.add(MyClass(42))
        with gimme.context():
            assert gimme.that(MyClass).a == 42

    def test_read_dependency_info_from_lower_layer(self):
        class MyClass:
            def __init__(self, a=None) -> None:
                self.a = a

        gimme.register(MyClass, lambda: MyClass(a=42))
        with gimme.context():
            assert gimme.that(MyClass).a == 42


class TestExceptions:
    def test_can_only_create_types(self, repo):
        with pytest.raises(TypeError):
            repo.create("invalid")

    def test_cannot_supply_both_cls_and_info_on_registration(self, repo):
        with pytest.raises(ValueError):
            repo.register(cls=int, info=gimme.types.DependencyInfo(int, int))

    def test_must_supply_either_cls_or_info_on_registration(self, repo):
        with pytest.raises(ValueError):
            repo.register()

    def test_cls_must_be_type_on_registration(self, repo):
        with pytest.raises(TypeError):
            repo.register(cls="invalid")

    def test_cannot_pop_base_layer(self, repo):
        repo.pop()
        with pytest.raises(IndexError):
            repo.pop()


def test_circular_dependencies(repo):
    class A:
        def __init__(self, c: "C"):
            ...

    class B:
        def __init__(self, a: A):
            ...

    @gimme.dependency
    class C:
        def __init__(self, b: B):
            ...

    with pytest.raises(gimme.exceptions.CircularDependency) as err:
        gimme.that(A)
    assert str(err.value) == "A -> C -> B"


def test_can_resolve_circular_dependencies_using_deferred_resolution():
    class A:
        b = gimme.later("B")

        def __init__(self):
            ...

    @gimme.dependency
    class B:
        def __init__(self, a: A):
            self.a = a

    obj = gimme.that(A)
    assert isinstance(obj, A)
    assert isinstance(obj.b, B)


def test_lookup_stack_is_cleared_after_successful_get(repo):
    repo.get(SimpleClass)
    assert not repo.lookup_stack


def test_lookup_stack_is_cleared_after_unsuccessful_get(repo):
    with pytest.raises(gimme.exceptions.CannotResolve):
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
        (Tuple[int], None),
        (list, None),
        (NamedTuple("Tuple", [("field", int)]), None),
    ],
)
def test_can_parse_collection(hint, expected):
    result = gimme.helpers.parse_type_hint(hint)
    if expected is not None:
        result = result.collection

    assert result is expected
