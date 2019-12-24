class CannotResolve(TypeError):
    pass


class PartiallyResolved(RuntimeError):
    pass


class CircularDependency(RuntimeError):
    pass
