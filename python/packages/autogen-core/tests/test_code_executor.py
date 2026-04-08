import textwrap

import pytest
from autogen_core.code_executor import (
    Alias,
    FunctionWithRequirements,
    FunctionWithRequirementsStr,
    ImportFromModule,
    with_requirements,
)
from autogen_core.code_executor._func_with_reqs import (
    _strip_with_requirements_decorator,
    build_python_functions_file,
)
from pandas import DataFrame, concat


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


def test_strip_with_requirements_decorator_single_line() -> None:
    code = '@with_requirements(python_packages=["pandas"])\ndef my_func():\n    return 1'
    result = _strip_with_requirements_decorator(code)
    assert result == "def my_func():\n    return 1"


def test_strip_with_requirements_decorator_multiline() -> None:
    code = textwrap.dedent("""\
        @with_requirements(
            python_packages=["httpx", "tenacity"],
            global_imports=[Alias("httpx", "ht")]
        )
        def fetch_url() -> str:
            return "hello"
    """).rstrip()
    result = _strip_with_requirements_decorator(code)
    assert "with_requirements" not in result
    assert "def fetch_url() -> str:" in result
    assert '    return "hello"' in result


def test_strip_with_requirements_preserves_other_decorators() -> None:
    code = textwrap.dedent("""\
        @with_requirements(
            python_packages=["httpx"],
            global_imports=[]
        )
        @retry(stop=stop_after_attempt(3))
        def fetch_url() -> str:
            return "hello"
    """).rstrip()
    result = _strip_with_requirements_decorator(code)
    assert "with_requirements" not in result
    assert "@retry(stop=stop_after_attempt(3))" in result
    assert "def fetch_url() -> str:" in result


def test_build_python_functions_file_multiline_decorator() -> None:
    @with_requirements(
        python_packages=["pandas"],
        global_imports=["pandas"],
    )
    def sample_func() -> str:
        return "test"

    result = build_python_functions_file([sample_func])
    assert "import pandas" in result
    assert "def sample_func" in result
    assert "with_requirements" not in result
