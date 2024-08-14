# File based from: https://github.com/microsoft/autogen/blob/main/test/coding/test_commandline_code_executor.py
# Credit to original authors

import asyncio
import os
import sys

import pytest
from azure.identity import DefaultAzureCredential
from agnext.components.code_executor import CodeBlock, AzureContainerCodeExecutor
from agnext.core import CancellationToken

UNIX_SHELLS = ["bash", "sh", "shell"]
WINDOWS_SHELLS = ["ps1", "pwsh", "powershell"]
PYTHON_VARIANTS = ["python", "Python", "py"]

ENVIRON_KEY_AZURE_POOL_ENDPOINT = "AZURE_POOL_ENDPOINT"

POOL_ENDPOINT = os.getenv(ENVIRON_KEY_AZURE_POOL_ENDPOINT)

@pytest.mark.skipif(
    not POOL_ENDPOINT,
    reason="do not run if pool endpoint is not defined",
)
@pytest.mark.asyncio
async def test_execute_code() -> None:
    assert POOL_ENDPOINT is not None
    cancellation_token = CancellationToken()
    executor = AzureContainerCodeExecutor(pool_management_endpoint=POOL_ENDPOINT, credential=DefaultAzureCredential())

    # Test single code block.
    code_blocks = [CodeBlock(code="import sys; print('hello world!')", language="python")]
    code_result = await executor.execute_code_blocks(code_blocks, cancellation_token)
    assert code_result.exit_code == 0 and "hello world!" in code_result.output

    # Test multiple code blocks.
    code_blocks = [
        CodeBlock(code="import sys; print('hello world!')", language="python"),
        CodeBlock(code="a = 100 + 100; print(a)", language="python"),
    ]
    code_result = await executor.execute_code_blocks(code_blocks, cancellation_token)
    assert (
        code_result.exit_code == 0
        and "hello world!" in code_result.output
        and "200" in code_result.output
    )

    # Test bash script.
    if sys.platform not in ["win32"]:
        code_blocks = [CodeBlock(code="echo 'hello world!'", language="bash")]
        code_result = await executor.execute_code_blocks(code_blocks, cancellation_token)
        assert "unknown language" in code_result.output
        assert code_result.exit_code == 1

    # Test running code.
    file_lines = ["import sys", "print('hello world!')", "a = 100 + 100", "print(a)"]
    code_blocks = [CodeBlock(code="\n".join(file_lines), language="python")]
    code_result = await executor.execute_code_blocks(code_blocks, cancellation_token)
    assert (
        code_result.exit_code == 0
        and "hello world!" in code_result.output
        and "200" in code_result.output
    )

@pytest.mark.skipif(
    not POOL_ENDPOINT,
    reason="do not run if pool endpoint is not defined",
)
@pytest.mark.asyncio
async def test_azure_container_code_executor_timeout() -> None:
    assert POOL_ENDPOINT is not None
    cancellation_token = CancellationToken()
    executor = AzureContainerCodeExecutor(pool_management_endpoint=POOL_ENDPOINT, credential=DefaultAzureCredential(), timeout=1)
    code_blocks = [CodeBlock(code="import time; time.sleep(10); print('hello world!')", language="python")]
    with pytest.raises(asyncio.TimeoutError):
        await executor.execute_code_blocks(code_blocks, cancellation_token)

@pytest.mark.skipif(
    not POOL_ENDPOINT,
    reason="do not run if pool endpoint is not defined",
)
@pytest.mark.asyncio
async def test_azure_container_code_executor_cancellation() -> None:
    assert POOL_ENDPOINT is not None
    cancellation_token = CancellationToken()
    executor = AzureContainerCodeExecutor(pool_management_endpoint=POOL_ENDPOINT, credential=DefaultAzureCredential())
    code_blocks = [CodeBlock(code="import time; time.sleep(10); print('hello world!')", language="python")]

    coro = executor.execute_code_blocks(code_blocks, cancellation_token)

    await asyncio.sleep(1)
    cancellation_token.cancel()

    with pytest.raises(asyncio.CancelledError):
        await coro
    