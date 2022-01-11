class CannotResolve(TypeError):
    """Raised when a :class:`~gimme.resolvers.Resolver` cannot resolve the dependencies of a class,
    and therefore cannot provide an instance
    """

    pass


class PartiallyResolved(RuntimeError):
    """Raised when an :class:`~gimme.resolvers.Resolver` did do some work on resolving
    dependencies, but not enough to be able to instantiate the class
    """

    pass


class CircularDependency(RuntimeError):
    """Raised when a circular dependency is detected and the requested class cannot be
    instantiated"""

    pass
