import textwrap

import pytest
from pandas import DataFrame, concat

from autogen_core.code_executor import (
    Alias,
    FunctionWithRequirements,
    FunctionWithRequirementsStr,
    ImportFromModule,
    with_requirements,
)
from autogen_core.code_executor._func_with_reqs import _strip_first_decorator, build_python_functions_file


def template_function() -> DataFrame:  # type: ignore
    data1 = {
        "name": ["John", "Anna"],
        "location": ["New York", "Paris"],
        "age": [24, 13],
    }
    data2 = {
        "name": ["Peter", "Linda"],
        "location": ["Berlin", "London"],
        "age": [53, 33],
    }
    df1 = DataFrame.from_dict(data1)  # type: ignore
    df2 = DataFrame.from_dict(data2)  # type: ignore
    return concat([df1, df2])  # type: ignore


def retry_like(*, stop: int, wait: int):
    def decorator(func):
        return func

    return decorator


@with_requirements(
    python_packages=["pandas", "tenacity"],
    global_imports=[ImportFromModule("pandas", ["DataFrame"])],
)
@retry_like(
    stop=3,
    wait=2,
)
def template_function_with_multiline_decorators() -> DataFrame:  # type: ignore
    return DataFrame.from_dict({"name": ["John"], "location": ["New York"], "age": [24]})  # type: ignore


@pytest.mark.asyncio
async def test_hashability_Import() -> None:
    function = FunctionWithRequirements.from_callable(  # type: ignore
        template_function,
        ["pandas"],
        [ImportFromModule("pandas", ["DataFrame", "concat"])],
    )
    functions_module = build_python_functions_file([function])  # type: ignore

    assert "from pandas import DataFrame, concat" in functions_module

    function2: FunctionWithRequirementsStr = FunctionWithRequirements.from_str(
        textwrap.dedent(
            """
            def template_function2():
                return pd.Series([1, 2])
            """
        ),
        "pandas",
        [Alias("pandas", "pd")],
    )
    functions_module2 = build_python_functions_file([function2])

    assert "import pandas as pd" in functions_module2


def test_build_python_functions_file_with_multiline_with_requirements_and_other_decorators() -> None:
    functions_module = build_python_functions_file([template_function_with_multiline_decorators])

    assert "python_packages=" not in functions_module
    assert "global_imports=" not in functions_module
    assert "@retry_like(" in functions_module
    assert "def template_function_with_multiline_decorators()" in functions_module
    compile(functions_module, "<generated_functions_module>", "exec")


def test_strip_first_decorator_single_line_decorator() -> None:
    code = "@decorator\ndef hello() -> int:\n    return 1\n"
    stripped = _strip_first_decorator(code)
    assert stripped.startswith("def hello()")
    compile(stripped, "<single_line_decorator>", "exec")


def test_strip_first_decorator_falls_back_for_syntax_error() -> None:
    code = "@decorator(\ndef hello() -> int:\n    return 1\n"
    stripped = _strip_first_decorator(code)
    assert stripped == "def hello() -> int:\n    return 1\n"


def test_strip_first_decorator_falls_back_for_non_function() -> None:
    code = "@decorator\nclass NotFunction:\n    pass\n"
    stripped = _strip_first_decorator(code)
    assert stripped == "class NotFunction:\n    pass\n"
