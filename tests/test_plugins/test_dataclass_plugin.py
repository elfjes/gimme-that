import attr
from attr import dataclass

import gimme


def test_can_get_dataclass():
    @dataclass
    class MyClass:
        a: int = attr.ib(factory=list)

    gimme.add(4)
    gimme._repository.get(gimme._Repository).register(MyClass, kwargs=dict(a=4))

    obj = gimme.that(MyClass)
    assert isinstance(obj, MyClass)
    assert obj.a == 4