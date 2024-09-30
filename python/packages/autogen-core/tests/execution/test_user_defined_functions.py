# File based from: https://github.com/microsoft/autogen/blob/main/test/coding/test_user_defined_functions.py
# Credit to original authors

import os
import tempfile

import polars
import pytest
from autogen_core.base import CancellationToken
from autogen_core.components.code_executor import (
    AzureContainerCodeExecutor,
    CodeBlock,
    FunctionWithRequirements,
    LocalCommandLineCodeExecutor,
    with_requirements,
)
from azure.identity import DefaultAzureCredential

ENVIRON_KEY_AZURE_POOL_ENDPOINT = "AZURE_POOL_ENDPOINT"

DUMMY_POOL_ENDPOINT = "DUMMY_POOL_ENDPOINT"
POOL_ENDPOINT = os.getenv(ENVIRON_KEY_AZURE_POOL_ENDPOINT)


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
        cancellation_token = CancellationToken()
        executor = LocalCommandLineCodeExecutor(work_dir=temp_dir, functions=[load_data])
        code = f"""from {executor.functions_module} import load_data
import polars

# Get first row's name
data = load_data()
print(data['name'][0])"""

        result = await executor.execute_code_blocks(
            code_blocks=[
                CodeBlock(language="python", code=code),
            ],
            cancellation_token=cancellation_token,
        )
        assert result.output == "John\n"
        assert result.exit_code == 0


@pytest.mark.skipif(
    not POOL_ENDPOINT,
    reason="do not run if pool endpoint is not defined",
)
@pytest.mark.asyncio
async def test_azure_can_load_function_with_reqs() -> None:
    assert POOL_ENDPOINT is not None
    cancellation_token = CancellationToken()
    azure_executor = AzureContainerCodeExecutor(
        pool_management_endpoint=POOL_ENDPOINT, credential=DefaultAzureCredential(), functions=[load_data]
    )
    # AzureContainerCodeExecutor doesn't use the functions module import
    code = """import polars

# Get first row's name
data = load_data()
print(data['name'][0])"""

    azure_result = await azure_executor.execute_code_blocks(
        code_blocks=[
            CodeBlock(language="python", code=code),
        ],
        cancellation_token=cancellation_token,
    )
    assert azure_result.output == "John\n"
    assert azure_result.exit_code == 0


@pytest.mark.asyncio
async def test_can_load_function() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        cancellation_token = CancellationToken()
        executor = LocalCommandLineCodeExecutor(work_dir=temp_dir, functions=[add_two_numbers])
        code = f"""from {executor.functions_module} import add_two_numbers
print(add_two_numbers(1, 2))"""

        result = await executor.execute_code_blocks(
            code_blocks=[
                CodeBlock(language="python", code=code),
            ],
            cancellation_token=cancellation_token,
        )
        assert result.output == "3\n"
        assert result.exit_code == 0


@pytest.mark.skipif(
    not POOL_ENDPOINT,
    reason="do not run if pool endpoint is not defined",
)
@pytest.mark.asyncio
async def test_azure_can_load_function() -> None:
    assert POOL_ENDPOINT is not None

    cancellation_token = CancellationToken()
    azure_executor = AzureContainerCodeExecutor(
        pool_management_endpoint=POOL_ENDPOINT, credential=DefaultAzureCredential(), functions=[add_two_numbers]
    )
    # AzureContainerCodeExecutor doesn't use the functions module import
    code = """print(add_two_numbers(1, 2))"""

    azure_result = await azure_executor.execute_code_blocks(
        code_blocks=[
            CodeBlock(language="python", code=code),
        ],
        cancellation_token=cancellation_token,
    )
    assert azure_result.output == "3\n"
    assert azure_result.exit_code == 0


@pytest.mark.asyncio
async def test_fails_for_function_incorrect_import() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        cancellation_token = CancellationToken()
        executor = LocalCommandLineCodeExecutor(work_dir=temp_dir, functions=[function_incorrect_import])
        code = f"""from {executor.functions_module} import function_incorrect_import
function_incorrect_import()"""

        with pytest.raises(ValueError):
            await executor.execute_code_blocks(
                code_blocks=[
                    CodeBlock(language="python", code=code),
                ],
                cancellation_token=cancellation_token,
            )


@pytest.mark.skipif(
    not POOL_ENDPOINT,
    reason="do not run if pool endpoint is not defined",
)
@pytest.mark.asyncio
async def test_azure_fails_for_function_incorrect_import() -> None:
    assert POOL_ENDPOINT is not None
    cancellation_token = CancellationToken()
    azure_executor = AzureContainerCodeExecutor(
        pool_management_endpoint=POOL_ENDPOINT,
        credential=DefaultAzureCredential(),
        functions=[function_incorrect_import],
    )
    code = """function_incorrect_import()"""

    with pytest.raises(ValueError):
        await azure_executor.execute_code_blocks(
            code_blocks=[
                CodeBlock(language="python", code=code),
            ],
            cancellation_token=cancellation_token,
        )


@pytest.mark.asyncio
async def test_fails_for_function_incorrect_dep() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        cancellation_token = CancellationToken()
        executor = LocalCommandLineCodeExecutor(work_dir=temp_dir, functions=[function_incorrect_dep])
        code = f"""from {executor.functions_module} import function_incorrect_dep
function_incorrect_dep()"""

        with pytest.raises(ValueError):
            await executor.execute_code_blocks(
                code_blocks=[
                    CodeBlock(language="python", code=code),
                ],
                cancellation_token=cancellation_token,
            )


@pytest.mark.skipif(
    not POOL_ENDPOINT,
    reason="do not run if pool endpoint is not defined",
)
@pytest.mark.asyncio
async def test_azure_fails_for_function_incorrect_dep() -> None:
    assert POOL_ENDPOINT is not None
    cancellation_token = CancellationToken()
    azure_executor = AzureContainerCodeExecutor(
        pool_management_endpoint=POOL_ENDPOINT, credential=DefaultAzureCredential(), functions=[function_incorrect_dep]
    )
    code = """function_incorrect_dep()"""

    with pytest.raises(ValueError):
        await azure_executor.execute_code_blocks(
            code_blocks=[
                CodeBlock(language="python", code=code),
            ],
            cancellation_token=cancellation_token,
        )


def test_formatted_prompt() -> None:
    assert_str = '''def add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
'''
    with tempfile.TemporaryDirectory() as temp_dir:
        executor = LocalCommandLineCodeExecutor(work_dir=temp_dir, functions=[add_two_numbers])

        result = executor.format_functions_for_prompt()
        assert assert_str in result

    azure_executor = AzureContainerCodeExecutor(
        pool_management_endpoint=DUMMY_POOL_ENDPOINT, credential=DefaultAzureCredential(), functions=[add_two_numbers]
    )

    azure_result = azure_executor.format_functions_for_prompt()
    assert assert_str in azure_result


def test_formatted_prompt_str_func() -> None:
    func = FunctionWithRequirements.from_str(
        '''
def add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b
'''
    )

    assert_str = '''def add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
'''

    with tempfile.TemporaryDirectory() as temp_dir:
        executor = LocalCommandLineCodeExecutor(work_dir=temp_dir, functions=[func])

        result = executor.format_functions_for_prompt()
        assert assert_str in result

    azure_executor = AzureContainerCodeExecutor(
        pool_management_endpoint=DUMMY_POOL_ENDPOINT, credential=DefaultAzureCredential(), functions=[func]
    )

    azure_result = azure_executor.format_functions_for_prompt()
    assert assert_str in azure_result


@pytest.mark.asyncio
async def test_can_load_str_function_with_reqs() -> None:
    func = FunctionWithRequirements.from_str(
        '''
def add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b
'''
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        cancellation_token = CancellationToken()

        executor = LocalCommandLineCodeExecutor(work_dir=temp_dir, functions=[func])
        code = f"""from {executor.functions_module} import add_two_numbers
print(add_two_numbers(1, 2))"""

        result = await executor.execute_code_blocks(
            code_blocks=[
                CodeBlock(language="python", code=code),
            ],
            cancellation_token=cancellation_token,
        )
        assert result.output == "3\n"
        assert result.exit_code == 0


@pytest.mark.skipif(
    not POOL_ENDPOINT,
    reason="do not run if pool endpoint is not defined",
)
@pytest.mark.asyncio
async def test_azure_can_load_str_function_with_reqs() -> None:
    assert POOL_ENDPOINT is not None
    cancellation_token = CancellationToken()
    func = FunctionWithRequirements.from_str(
        '''
def add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b
'''
    )
    azure_executor = AzureContainerCodeExecutor(
        pool_management_endpoint=POOL_ENDPOINT, credential=DefaultAzureCredential(), functions=[func]
    )
    code = """print(add_two_numbers(1, 2))"""

    azure_result = await azure_executor.execute_code_blocks(
        code_blocks=[
            CodeBlock(language="python", code=code),
        ],
        cancellation_token=cancellation_token,
    )
    assert azure_result.output == "3\n"
    assert azure_result.exit_code == 0


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
    func = FunctionWithRequirements.from_str(
        '''
def add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b
'''
    )
    with tempfile.TemporaryDirectory() as temp_dir:
        cancellation_token = CancellationToken()

        executor = LocalCommandLineCodeExecutor(work_dir=temp_dir, functions=[func])
        code = f"""from {executor.functions_module} import add_two_numbers
print(add_two_numbers(object(), False))"""

        result = await executor.execute_code_blocks(
            code_blocks=[
                CodeBlock(language="python", code=code),
            ],
            cancellation_token=cancellation_token,
        )
        assert "TypeError: unsupported operand type(s) for +:" in result.output
        assert result.exit_code == 1


@pytest.mark.skipif(
    not POOL_ENDPOINT,
    reason="do not run if pool endpoint is not defined",
)
@pytest.mark.asyncio
async def test_azure_cant_run_broken_str_function_with_reqs() -> None:
    assert POOL_ENDPOINT is not None
    cancellation_token = CancellationToken()
    func = FunctionWithRequirements.from_str(
        '''
def add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b
'''
    )

    azure_executor = AzureContainerCodeExecutor(
        pool_management_endpoint=POOL_ENDPOINT, credential=DefaultAzureCredential(), functions=[func]
    )
    code = """print(add_two_numbers(object(), False))"""

    azure_result = await azure_executor.execute_code_blocks(
        code_blocks=[
            CodeBlock(language="python", code=code),
        ],
        cancellation_token=cancellation_token,
    )
    # result.output = result.output.encode().decode('unicode_escape')
    assert "TypeError: unsupported operand type(s) for +:" in azure_result.output
    assert azure_result.exit_code == 1
