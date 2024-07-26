# File based from: https://github.com/microsoft/autogen/blob/main/test/coding/test_user_defined_functions.py
# Credit to original authors

import tempfile

import polars
import pytest
from agnext.components.code_executor import (
    CodeBlock,
    FunctionWithRequirements,
    LocalCommandLineCodeExecutor,
    with_requirements,
)


def add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


@with_requirements(python_packages=["polars"], global_imports=["polars"])
def load_data() -> polars.DataFrame:
    """Load some sample data.

    Returns:
        polars.DataFrame: A DataFrame with the following columns: name(str), location(str), age(int)
    """
    data = {
        "name": ["John", "Anna", "Peter", "Linda"],
        "location": ["New York", "Paris", "Berlin", "London"],
        "age": [24, 13, 53, 33],
    }
    return polars.DataFrame(data)


@with_requirements(global_imports=["NOT_A_REAL_PACKAGE"])
def function_incorrect_import() -> "polars.DataFrame":
    return polars.DataFrame()


@with_requirements(python_packages=["NOT_A_REAL_PACKAGE"])
def function_incorrect_dep() -> "polars.DataFrame":
    return polars.DataFrame()


def function_missing_reqs() -> "polars.DataFrame":
    return polars.DataFrame()


@pytest.mark.asyncio
async def test_can_load_function_with_reqs() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        executor = LocalCommandLineCodeExecutor(
            work_dir=temp_dir, functions=[load_data]
        )
        code = f"""from {executor.functions_module} import load_data
import polars

# Get first row's name
data = load_data()
print(data['name'][0])"""

        result = await executor.execute_code_blocks(
            code_blocks=[
                CodeBlock(language="python", code=code),
            ]
        )
        assert result.output == "John\n"
        assert result.exit_code == 0


@pytest.mark.asyncio
async def test_can_load_function() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        executor = LocalCommandLineCodeExecutor(
            work_dir=temp_dir, functions=[add_two_numbers]
        )
        code = f"""from {executor.functions_module} import add_two_numbers
print(add_two_numbers(1, 2))"""

        result = await executor.execute_code_blocks(
            code_blocks=[
                CodeBlock(language="python", code=code),
            ]
        )
        assert result.output == "3\n"
        assert result.exit_code == 0


@pytest.mark.asyncio
async def test_fails_for_function_incorrect_import() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        executor = LocalCommandLineCodeExecutor(
            work_dir=temp_dir, functions=[function_incorrect_import]
        )
        code = f"""from {executor.functions_module} import function_incorrect_import
function_incorrect_import()"""

        with pytest.raises(ValueError):
            await executor.execute_code_blocks(
                code_blocks=[
                    CodeBlock(language="python", code=code),
                ]
            )


@pytest.mark.asyncio
async def test_fails_for_function_incorrect_dep() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        executor = LocalCommandLineCodeExecutor(
            work_dir=temp_dir, functions=[function_incorrect_dep]
        )
        code = f"""from {executor.functions_module} import function_incorrect_dep
function_incorrect_dep()"""

        with pytest.raises(ValueError):
            await executor.execute_code_blocks(
                code_blocks=[
                    CodeBlock(language="python", code=code),
                ]
            )


def test_formatted_prompt() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        executor = LocalCommandLineCodeExecutor(
            work_dir=temp_dir, functions=[add_two_numbers]
        )

        result = executor.format_functions_for_prompt()
        assert (
            '''def add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
'''
            in result
        )


def test_formatted_prompt_str_func() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        func = FunctionWithRequirements.from_str(
            '''
def add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b
'''
        )
        executor = LocalCommandLineCodeExecutor(work_dir=temp_dir, functions=[func])

        result = executor.format_functions_for_prompt()
        assert (
            '''def add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
'''
            in result
        )


@pytest.mark.asyncio
async def test_can_load_str_function_with_reqs() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        func = FunctionWithRequirements.from_str(
            '''
def add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b
'''
        )

        executor = LocalCommandLineCodeExecutor(work_dir=temp_dir, functions=[func])
        code = f"""from {executor.functions_module} import add_two_numbers
print(add_two_numbers(1, 2))"""

        result = await executor.execute_code_blocks(
            code_blocks=[
                CodeBlock(language="python", code=code),
            ]
        )
        assert result.output == "3\n"
        assert result.exit_code == 0


def test_cant_load_broken_str_function_with_reqs() -> None:

    with pytest.raises(ValueError):
        _ = FunctionWithRequirements.from_str(
            '''
invaliddef add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b
'''
        )


@pytest.mark.asyncio
async def test_cant_run_broken_str_function_with_reqs() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        func = FunctionWithRequirements.from_str(
            '''
def add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b
'''
        )

        executor = LocalCommandLineCodeExecutor(work_dir=temp_dir, functions=[func])
        code = f"""from {executor.functions_module} import add_two_numbers
print(add_two_numbers(object(), False))"""

        result = await executor.execute_code_blocks(
            code_blocks=[
                CodeBlock(language="python", code=code),
            ]
        )
        assert "TypeError: unsupported operand type(s) for +:" in result.output
        assert result.exit_code == 1
