from __future__ import annotations
import inspect
import functools
from typing import Any, Callable, List, TypeVar, Generic, Union
from typing_extensions import ParamSpec
from textwrap import indent, dedent
from dataclasses import dataclass, field

T = TypeVar("T")
P = ParamSpec("P")


def _to_code(func: Union[FunctionWithRequirements[T, P], Callable[P, T]]) -> str:
    code = inspect.getsource(func)
    # Strip the decorator
    if code.startswith("@"):
        code = code[code.index("\n") + 1 :]
    return code


@dataclass
class Alias:
    name: str
    alias: str


@dataclass
class ImportFromModule:
    module: str
    imports: List[Union[str, Alias]]


Import = Union[str, ImportFromModule, Alias]


def _import_to_str(im: Import) -> str:
    if isinstance(im, str):
        return f"import {im}"
    elif isinstance(im, Alias):
        return f"import {im.name} as {im.alias}"
    else:

        def to_str(i: Union[str, Alias]) -> str:
            if isinstance(i, str):
                return i
            else:
                return f"{i.name} as {i.alias}"

        imports = ", ".join(map(to_str, im.imports))
        return f"from {im.module} import {imports}"


@dataclass
class FunctionWithRequirements(Generic[T, P]):
    func: Callable[P, T]
    python_packages: List[str] = field(default_factory=list)
    global_imports: List[Import] = field(default_factory=list)

    @classmethod
    def from_callable(
        cls, func: Callable[P, T], python_packages: List[str] = [], global_imports: List[Import] = []
    ) -> FunctionWithRequirements[T, P]:
        return cls(python_packages=python_packages, global_imports=global_imports, func=func)

    # Type this based on F
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        return self.func(*args, **kwargs)


def with_requirements(
    python_packages: List[str] = [], global_imports: List[Import] = []
) -> Callable[[Callable[P, T]], FunctionWithRequirements[T, P]]:
    """Decorate a function with package and import requirements

    Args:
        python_packages (List[str], optional): Packages required to function. Can include version info.. Defaults to [].
        global_imports (List[Import], optional): Required imports. Defaults to [].

    Returns:
        Callable[[Callable[P, T]], FunctionWithRequirements[T, P]]: The decorated function
    """

    def wrapper(func: Callable[P, T]) -> FunctionWithRequirements[T, P]:
        func_with_reqs = FunctionWithRequirements(
            python_packages=python_packages, global_imports=global_imports, func=func
        )

        functools.update_wrapper(func_with_reqs, func)
        return func_with_reqs

    return wrapper


def _build_python_functions_file(funcs: List[Union[FunctionWithRequirements[Any, P], Callable[..., Any]]]) -> str:
    # First collect all global imports
    global_imports = set()
    for func in funcs:
        if isinstance(func, FunctionWithRequirements):
            global_imports.update(func.global_imports)

    content = "\n".join(map(_import_to_str, global_imports)) + "\n\n"

    for func in funcs:
        content += _to_code(func) + "\n\n"

    return content


def to_stub(func: Callable[..., Any]) -> str:
    """Generate a stub for a function as a string

    Args:
        func (Callable[..., Any]): The function to generate a stub for

    Returns:
        str: The stub for the function
    """
    content = f"def {func.__name__}{inspect.signature(func)}:\n"
    docstring = func.__doc__

    if docstring:
        docstring = dedent(docstring)
        docstring = '"""' + docstring + '"""'
        docstring = indent(docstring, "    ")
        content += docstring + "\n"

    content += "    ..."
    return content
