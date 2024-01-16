import typing
from abc import ABC, abstractmethod
from typing import Any, Callable, List, Optional, Protocol, Tuple, Type, TypeVar, Union

__all__ = ["Condition"]


class Condition(ABC):
    """Abstract base class for conditions."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize the condition.

        Args:
            args: positional arguments to be passed to the condition.
            kwargs: keyword arguments to be passed to the condition.
        """
        self.args = args
        self.kwargs = kwargs

    @abstractmethod
    def __call__(self, x: Any) -> bool:
        ...

    @classmethod
    def true(cls) -> "Always":
        return Always()

    @classmethod
    def false(cls) -> "Never":
        return Never()

    @staticmethod
    def isinstance(cls: Type[Any], *args: Any, **kwargs: Any) -> "IsInstance":
        return IsInstance(cls, *args, **kwargs)

    @staticmethod
    def evaluate(f: typing.Callable[..., bool], *args: Any, **kwargs: Any) -> "Evaluate":
        return Evaluate(f, *args, **kwargs)

    def __and__(self, other: "Condition") -> "Condition":
        """Combine two conditions with the operator `&`.

        Args:
            other: The other condition.

        Returns:
            A new condition that is the logical and of the two conditions.
        """
        return AllOf([self, other])

    def __or__(self, other: "Condition") -> "Condition":
        """Combine two conditions with the operator `|`.

        Args:
            other: The other condition.

        Returns:
            A new condition that is the logical or of the two conditions.
        """
        return AllOf([self, other])


class Always(Condition):
    """Condition that always returns True."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize the condition.

        Args:
            args: positional arguments to be passed to the condition.
            kwargs: keyword arguments to be passed to the condition.
        """
        super().__init__(*args, **kwargs)

    def __call__(self, x: Any) -> bool:
        """Always return True.

        Args:
            x: Ignored.

        Returns:
            Always True.

        """
        return True


class Never(Condition):
    """Condition that always returns False."""

    def __init__(self, *args: Any, **kwargs: Any):
        """Initialize the condition.

        Args:
            args: positional arguments to be passed to the condition.
            kwargs: keyword arguments to be passed to the condition.
        """
        super().__init__(*args, **kwargs)

    def __call__(self, x: Any) -> bool:
        """Always return False.

        Args:
            x: The object to check.

        Returns:
            Always False.

        """
        return False


class IsInstance(Condition):
    """Condition for an instance of a class."""

    def __init__(self, cls: type, *args: Any, **kwargs: Any):
        """Initialize the condition.

        Args:
            cls: The class to check.

        Example:
            ```python
            from autogen.intercept import IsInstance

            class A:
                pass

            a = A()
            assert IsInstance(A)(a)
            assert not IsInstance(int)(a)
            ```
        """
        self.cls = cls

    def __call__(self, x: Any) -> bool:
        """Check if x is an instance of the class.

        Returns:
            True if x is an instance of the class, False otherwise.

        """
        return isinstance(x, self.cls)


class Evaluate(Condition):
    """Condition for a function."""

    def __init__(self, f: typing.Callable[..., bool], *args: Any, **kwargs: Any):
        """Initialize the condition.

        Args:
            f: The function to be called on an object.
            args: positional arguments to be passed to the function.
            kwargs: keyword arguments to be passed to the function.

        Example:
            ```python
            from autogen.middleware.conditions import Evaluate

            def f(x: float) -> bool:
                return x > 0

            assert Evaluate(f)(1)
            assert Function(lambda *args, **kwargs: x == 0)(0, 1, 2, a=1, b=2, c=3)
            ```
        """
        self.f = f
        self.args = args
        self.kwargs = kwargs

    def __call__(self, x: Any) -> bool:
        """Check if the object is an instance of the class.

        Args:
            x: The object to check.

        Returns:


        """
        return self.f(x, *self.args, **self.kwargs)


class AllOf(Condition):
    """Condition for a function."""

    def __init__(self, conditions: List[Condition], *args: Any, lazy_eval: bool = True, **kwargs: Any):
        """Initialize the condition.

        Args:
            conditions: A list of conditions to check.
            lazy_eval: If True, the conditions are evaluated lazily. The
              first condition that returns False will stop the evaluation.
            args: positional arguments to be passed to each condition.
            kwargs: keyword arguments to be passed to each condition.

        Example:
            ```python
            from autogen.midleware.conditions import Function, AllOf

            def f(x: float) -> bool:
                return x > 0

            def g(x: float) -> bool:
                return x < 1

            assert AllOf([Function(f), Function(g)])(0.5)
            assert not AllOf([Function(f), Function(g)])(1.5)
            ```
        """
        self.conditions = conditions
        self.args = args
        self.lazy_eval = lazy_eval
        self.kwargs = kwargs

    def __call__(self, x: Any) -> bool:
        """Check that all

        Args:
            x: The object to check.

        Returns:
            True if the object is an instance of the class, False otherwise.

        """
        if self.lazy_eval:
            # lazy evaluation returns as soon as a condition returns False
            for c in self.conditions:
                if not c(x, *self.args, **self.kwargs):
                    return False
            return True
        else:
            # eager evaluation evaluates all conditions
            xs = [c(x, *self.args, **self.kwargs) for c in self.conditions]

            return all(xs)

    def __and__(self, other: "Condition") -> "Condition":
        """Combine two conditions with the operator `&`.

        Args:
            other: The other condition.

        Returns:
            A new condition that is the logical and of the two conditions.
        """
        self.conditions.append(other)
        return self


class AnyOf(Condition):
    """Condition for a function."""

    def __init__(self, conditions: List[Condition], *args: Any, lazy_eval: bool = True, **kwargs: Any):
        """Initialize the condition.

        Args:
            conditions: A list of conditions to check.
            lazy_eval: If True, the conditions are evaluated lazily. The
              first condition that returns False will stop the evaluation.
            args: positional arguments to be passed to each condition.
            kwargs: keyword arguments to be passed to each condition.

        Example:
            ```python
            from autogen.midleware.conditions import Function, AllOf

            def f(x: float) -> bool:
                return x > 0

            def g(x: float) -> bool:
                return x < 1

            assert AllOf([Function(f), Function(g)])(0.5)
            assert not AllOf([Function(f), Function(g)])(1.5)
            ```
        """
        self.conditions = conditions
        self.args = args
        self.lazy_eval = lazy_eval
        self.kwargs = kwargs

    def __call__(self, x: Any) -> bool:
        """Check that all

        Args:
            x: The object to check.

        Returns:
            True if the object is an instance of the class, False otherwise.

        """
        if self.lazy_eval:
            # lazy evaluation returns as soon as a condition returns False
            for c in self.conditions:
                if not c(x, *self.args, **self.kwargs):
                    return False
            return True
        else:
            # eager evaluation evaluates all conditions
            xs = [c(x, *self.args, **self.kwargs) for c in self.conditions]

            return all(xs)

    def __or__(self, other: "Condition") -> "Condition":
        """Combine two conditions with the operator `|`.

        Args:
            other: The other condition.

        Returns:
            A new condition that is the logical or of the two conditions.
        """
        self.conditions.append(other)
        return self
