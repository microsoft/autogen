import tempfile

import pytest

from autogen.coding.base import CodeBlock
from autogen.coding.local_commandline_code_executor import LocalCommandLineCodeExecutor

try:
    import pandas
except ImportError:
    skip = True
else:
    skip = False

from autogen.coding.func_with_reqs import FunctionWithRequirements, with_requirements

classes_to_test = [LocalCommandLineCodeExecutor]


def add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


@with_requirements(python_packages=["pandas"], global_imports=["pandas"])
def load_data() -> "pandas.DataFrame":
    """Load some sample data.

    Returns:
        pandas.DataFrame: A DataFrame with the following columns: name(str), location(str), age(int)
    """
    data = {
        "name": ["John", "Anna", "Peter", "Linda"],
        "location": ["New York", "Paris", "Berlin", "London"],
        "age": [24, 13, 53, 33],
    }
    return pandas.DataFrame(data)


@with_requirements(global_imports=["NOT_A_REAL_PACKAGE"])
def function_incorrect_import() -> "pandas.DataFrame":
    return pandas.DataFrame()


@with_requirements(python_packages=["NOT_A_REAL_PACKAGE"])
def function_incorrect_dep() -> "pandas.DataFrame":
    return pandas.DataFrame()


def function_missing_reqs() -> "pandas.DataFrame":
    return pandas.DataFrame()


@pytest.mark.parametrize("cls", classes_to_test)
@pytest.mark.skipif(skip, reason="pandas not installed")
def test_can_load_function_with_reqs(cls) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        executor = cls(work_dir=temp_dir, functions=[load_data])
        code = f"""from {executor.functions_module} import load_data
import pandas

# Get first row's name
print(load_data().iloc[0]['name'])"""

        result = executor.execute_code_blocks(
            code_blocks=[
                CodeBlock(language="python", code=code),
            ]
        )
        assert result.output == "John\n"
        assert result.exit_code == 0


@pytest.mark.parametrize("cls", classes_to_test)
@pytest.mark.skipif(skip, reason="pandas not installed")
def test_can_load_function(cls) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        executor = cls(work_dir=temp_dir, functions=[add_two_numbers])
        code = f"""from {executor.functions_module} import add_two_numbers
print(add_two_numbers(1, 2))"""

        result = executor.execute_code_blocks(
            code_blocks=[
                CodeBlock(language="python", code=code),
            ]
        )
        assert result.output == "3\n"
        assert result.exit_code == 0


# TODO - only run this test for containerized executors, as the environment is not guaranteed to have pandas installed
# It is common for the local environment to have pandas installed, so this test will not work as expected
# @pytest.mark.parametrize("cls", classes_to_test)
# @pytest.mark.skipif(skip, reason="pandas not installed")
# def test_fails_for_missing_reqs(cls) -> None:
#     with tempfile.TemporaryDirectory() as temp_dir:
#         executor = cls(work_dir=temp_dir, functions=[function_missing_reqs])
#         code = f"""from {executor.functions_module} import function_missing_reqs
# function_missing_reqs()"""

#         with pytest.raises(ValueError):
#             executor.execute_code_blocks(
#                 code_blocks=[
#                     CodeBlock(language="python", code=code),
#                 ]
#             )


@pytest.mark.parametrize("cls", classes_to_test)
@pytest.mark.skipif(skip, reason="pandas not installed")
def test_fails_for_function_incorrect_import(cls) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        executor = cls(work_dir=temp_dir, functions=[function_incorrect_import])
        code = f"""from {executor.functions_module} import function_incorrect_import
function_incorrect_import()"""

        with pytest.raises(ValueError):
            executor.execute_code_blocks(
                code_blocks=[
                    CodeBlock(language="python", code=code),
                ]
            )


@pytest.mark.parametrize("cls", classes_to_test)
@pytest.mark.skipif(skip, reason="pandas not installed")
def test_fails_for_function_incorrect_dep(cls) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        executor = cls(work_dir=temp_dir, functions=[function_incorrect_dep])
        code = f"""from {executor.functions_module} import function_incorrect_dep
function_incorrect_dep()"""

        with pytest.raises(ValueError):
            executor.execute_code_blocks(
                code_blocks=[
                    CodeBlock(language="python", code=code),
                ]
            )


@pytest.mark.parametrize("cls", classes_to_test)
def test_formatted_prompt(cls) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        executor = cls(work_dir=temp_dir, functions=[add_two_numbers])

        result = executor.format_functions_for_prompt()
        assert (
            '''def add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
'''
            in result
        )


@pytest.mark.parametrize("cls", classes_to_test)
def test_formatted_prompt_str_func(cls) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        func = FunctionWithRequirements.from_str(
            '''
def add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b
'''
        )
        executor = cls(work_dir=temp_dir, functions=[func])

        result = executor.format_functions_for_prompt()
        assert (
            '''def add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
'''
            in result
        )


@pytest.mark.parametrize("cls", classes_to_test)
def test_can_load_str_function_with_reqs(cls) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        func = FunctionWithRequirements.from_str(
            '''
def add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b
'''
        )

        executor = cls(work_dir=temp_dir, functions=[func])
        code = f"""from {executor.functions_module} import add_two_numbers
print(add_two_numbers(1, 2))"""

        result = executor.execute_code_blocks(
            code_blocks=[
                CodeBlock(language="python", code=code),
            ]
        )
        assert result.output == "3\n"
        assert result.exit_code == 0


@pytest.mark.parametrize("cls", classes_to_test)
def test_cant_load_broken_str_function_with_reqs(cls) -> None:

    with pytest.raises(ValueError):
        _ = FunctionWithRequirements.from_str(
            '''
invaliddef add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b
'''
        )


@pytest.mark.parametrize("cls", classes_to_test)
def test_cant_run_broken_str_function_with_reqs(cls) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        func = FunctionWithRequirements.from_str(
            '''
def add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b
'''
        )

        executor = cls(work_dir=temp_dir, functions=[func])
        code = f"""from {executor.functions_module} import add_two_numbers
print(add_two_numbers(object(), False))"""

        result = executor.execute_code_blocks(
            code_blocks=[
                CodeBlock(language="python", code=code),
            ]
        )
        assert "TypeError: unsupported operand type(s) for +:" in result.output
        assert result.exit_code == 1
