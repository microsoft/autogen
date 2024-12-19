# File based from: https://github.com/microsoft/autogen/blob/main/autogen/coding/func_with_reqs.py
# Credit to original authors

from __future__ import annotations

import functools
import inspect
from dataclasses import dataclass, field
from importlib.abc import SourceLoader
from importlib.util import module_from_spec, spec_from_loader
from textwrap import dedent, indent
from typing import Any, Callable, Generic, List, Sequence, Set, TypeVar, Union

from typing_extensions import ParamSpec, deprecated

T = TypeVar("T")
P = ParamSpec("P")


def _to_code(func: Union[FunctionWithRequirements[T, P], Callable[P, T], FunctionWithRequirementsStr]) -> str:  # type: ignore
    if isinstance(func, FunctionWithRequirementsStr):  # type: ignore
        return func.func

    code = inspect.getsource(func)
    # Strip the decorator
    if code.startswith("@"):
        code = code[code.index("\n") + 1 :]
    return code


@deprecated("Moved to autogen_core.code_executor.Alias. This alias will be removed in 0.4.0.")
@dataclass
class Alias:
    name: str
    alias: str


@deprecated("Moved to autogen_core.code_executor.ImportFromModule. This alias will be removed in 0.4.0.")
@dataclass
class ImportFromModule:
    module: str
    imports: List[Union[str, Alias]]  # type: ignore


Import = Union[str, ImportFromModule, Alias]  # type: ignore


def _import_to_str(im: Import) -> str:
    if isinstance(im, str):
        return f"import {im}"
    elif isinstance(im, Alias):  # type: ignore
        return f"import {im.name} as {im.alias}"
    else:

        def to_str(i: Union[str, Alias]) -> str:  # type: ignore
            if isinstance(i, str):
                return i
            else:
                return f"{i.name} as {i.alias}"

        imports = ", ".join(map(to_str, im.imports))
        return f"from {im.module} import {imports}"


class _StringLoader(SourceLoader):
    def __init__(self, data: str):
        self.data = data

    def get_source(self, fullname: str) -> str:
        return self.data

    def get_data(self, path: str) -> bytes:
        return self.data.encode("utf-8")

    def get_filename(self, fullname: str) -> str:
        return "<not a real path>/" + fullname + ".py"


@deprecated("Moved to autogen_core.code_executor.CodeBlock. This alias will be removed in 0.4.0.")
@dataclass
class FunctionWithRequirementsStr:
    func: str
    compiled_func: Callable[..., Any]
    _func_name: str
    python_packages: Sequence[str] = field(default_factory=list)
    global_imports: Sequence[Import] = field(default_factory=list)

    def __init__(self, func: str, python_packages: Sequence[str] = [], global_imports: Sequence[Import] = []):
        self.func = func
        self.python_packages = python_packages
        self.global_imports = global_imports

        module_name = "func_module"
        loader = _StringLoader(func)
        spec = spec_from_loader(module_name, loader)
        if spec is None:
            raise ValueError("Could not create spec")
        module = module_from_spec(spec)
        if spec.loader is None:
            raise ValueError("Could not create loader")

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            raise ValueError(f"Could not compile function: {e}") from e

        functions = inspect.getmembers(module, inspect.isfunction)
        if len(functions) != 1:
            raise ValueError("The string must contain exactly one function")

        self._func_name, self.compiled_func = functions[0]

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError("String based function with requirement objects are not directly callable")


@deprecated("Moved to autogen_core.code_executor.FunctionWithRequirements. This alias will be removed in 0.4.0.")
@dataclass
class FunctionWithRequirements(Generic[T, P]):
    func: Callable[P, T]
    python_packages: Sequence[str] = field(default_factory=list)
    global_imports: Sequence[Import] = field(default_factory=list)

    @classmethod
    def from_callable(
        cls, func: Callable[P, T], python_packages: Sequence[str] = [], global_imports: Sequence[Import] = []
    ) -> FunctionWithRequirements[T, P]:  # type: ignore
        return cls(python_packages=python_packages, global_imports=global_imports, func=func)

    @staticmethod
    def from_str(
        func: str, python_packages: Sequence[str] = [], global_imports: Sequence[Import] = []
    ) -> FunctionWithRequirementsStr:  # type: ignore
        return FunctionWithRequirementsStr(func=func, python_packages=python_packages, global_imports=global_imports)  # type: ignore

    # Type this based on F
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        return self.func(*args, **kwargs)


@deprecated("Moved to autogen_core.code_executor.with_requirements. This alias will be removed in 0.4.0.")
def with_requirements(
    python_packages: Sequence[str] = [], global_imports: Sequence[Import] = []
) -> Callable[[Callable[P, T]], FunctionWithRequirements[T, P]]:  # type: ignore
    """Decorate a function with package and import requirements

    Args:
        python_packages (List[str], optional): Packages required to function. Can include version info.. Defaults to [].
        global_imports (List[Import], optional): Required imports. Defaults to [].

    Returns:
        Callable[[Callable[P, T]], FunctionWithRequirements[T, P]]: The decorated function
    """

    def wrapper(func: Callable[P, T]) -> FunctionWithRequirements[T, P]:  # type: ignore
        func_with_reqs = FunctionWithRequirements(  # type: ignore
            python_packages=python_packages, global_imports=global_imports, func=func
        )

        functools.update_wrapper(func_with_reqs, func)
        return func_with_reqs

    return wrapper


def build_python_functions_file(
    funcs: Sequence[Union[FunctionWithRequirements[Any, P], Callable[..., Any], FunctionWithRequirementsStr]],  # type: ignore
) -> str:
    """:meta private:"""
    # First collect all global imports
    global_imports: Set[Import] = set()
    for func in funcs:
        if isinstance(func, (FunctionWithRequirements, FunctionWithRequirementsStr)):  # type: ignore
            global_imports.update(func.global_imports)

    content = "\n".join(map(_import_to_str, global_imports)) + "\n\n"

    for func in funcs:
        content += _to_code(func) + "\n\n"

    return content


def to_stub(func: Union[Callable[..., Any], FunctionWithRequirementsStr]) -> str:  # type: ignore
    """Generate a stub for a function as a string

    Args:
        func (Callable[..., Any]): The function to generate a stub for

    Returns:
        str: The stub for the function
    """
    if isinstance(func, FunctionWithRequirementsStr):  # type: ignore
        return to_stub(func.compiled_func)

    content = f"def {func.__name__}{inspect.signature(func)}:\n"
    docstring = func.__doc__

    if docstring:
        docstring = dedent(docstring)
        docstring = '"""' + docstring + '"""'
        docstring = indent(docstring, "    ")
        content += docstring + "\n"

    content += "    ..."
    return content
