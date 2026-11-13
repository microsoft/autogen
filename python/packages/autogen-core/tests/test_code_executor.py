import textwrap

import pytest
from autogen_core.code_executor import (
    Alias,
    FunctionWithRequirements,
    FunctionWithRequirementsStr,
    ImportFromModule,
    with_requirements,
)
from autogen_core.code_executor._func_with_reqs import build_python_functions_file
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


def test_default_requirement_arguments_are_immutable() -> None:
    function = FunctionWithRequirements.from_callable(template_function)  # type: ignore
    assert function.python_packages == ()
    assert function.global_imports == ()

    string_function = FunctionWithRequirements.from_str("def template_function2():\n    return None")
    assert string_function.python_packages == ()
    assert string_function.global_imports == ()

    @with_requirements()
    def decorated_function() -> None:
        return None

    assert decorated_function.python_packages == ()
    assert decorated_function.global_imports == ()
