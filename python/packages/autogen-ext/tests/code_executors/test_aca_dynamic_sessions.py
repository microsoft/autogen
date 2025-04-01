# File based from: https://github.com/microsoft/autogen/blob/main/test/coding/test_commandline_code_executor.py
# Credit to original authors

import asyncio
import os
import sys
import tempfile

import pytest
from anyio import open_file
from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock
from autogen_ext.code_executors.azure import ACADynamicSessionsCodeExecutor
from azure.identity import DefaultAzureCredential

UNIX_SHELLS = ["bash", "sh", "shell"]
WINDOWS_SHELLS = ["ps1", "pwsh", "powershell"]
PYTHON_VARIANTS = ["python", "Python", "py"]

ENVIRON_KEY_AZURE_POOL_ENDPOINT = "AZURE_POOL_ENDPOINT"

POOL_ENDPOINT = os.getenv(ENVIRON_KEY_AZURE_POOL_ENDPOINT)


def test_session_id_preserved_if_passed() -> None:
    executor = ACADynamicSessionsCodeExecutor(
        pool_management_endpoint=POOL_ENDPOINT, credential=DefaultAzureCredential()
    )
    session_id = "test_session_id"
    executor._session_id = session_id
    assert executor._session_id == session_id


def test_session_id_generated_if_not_passed() -> None:
    executor = ACADynamicSessionsCodeExecutor(
        pool_management_endpoint=POOL_ENDPOINT, credential=DefaultAzureCredential()
    )
    assert executor._session_id is not None
    assert len(executor._session_id) > 0


@pytest.mark.skipif(
    not POOL_ENDPOINT,
    reason="do not run if pool endpoint is not defined",
)
@pytest.mark.asyncio
async def test_execute_code() -> None:
    assert POOL_ENDPOINT is not None
    cancellation_token = CancellationToken()
    executor = ACADynamicSessionsCodeExecutor(
        pool_management_endpoint=POOL_ENDPOINT, credential=DefaultAzureCredential()
    )
    await executor.start()

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
    assert code_result.exit_code == 0 and "hello world!" in code_result.output and "200" in code_result.output

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
    assert code_result.exit_code == 0 and "hello world!" in code_result.output and "200" in code_result.output
    await executor.stop()


@pytest.mark.skipif(
    not POOL_ENDPOINT,
    reason="do not run if pool endpoint is not defined",
)
@pytest.mark.asyncio
async def test_execute_code_create_image() -> None:
    assert POOL_ENDPOINT is not None
    cancellation_token = CancellationToken()
    executor = ACADynamicSessionsCodeExecutor(
        pool_management_endpoint=POOL_ENDPOINT,
        credential=DefaultAzureCredential(),
        suppress_result_output=True,
    )

    # Test code block that creates an image.
    # This code cuases the session call to return a result with the base64 encoded output
    # By default, this is appended to the output
    # This test verifies that suppress_result_output prevents this from happening
    code_blocks = [
        CodeBlock(
            code="""
import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Create a figure and axis
fig, ax = plt.subplots(figsize=(6, 6))

# Add a circle
circle = patches.Circle((0.5, 0.5), 0.3, color='blue', fill=True)
ax.add_patch(circle)


# Set the axis limits and aspect ratio
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)
ax.set_aspect('equal')
ax.axis('off')  # Turn off the axis

# Save the image to a file
plt.savefig("circle.png", bbox_inches='tight')
print("Saved to circle.png")
""",
            language="python",
        ),
    ]
    code_result = await executor.execute_code_blocks(code_blocks, cancellation_token)
    assert code_result.exit_code == 0 and "base64_data" not in code_result.output


@pytest.mark.skipif(
    not POOL_ENDPOINT,
    reason="do not run if pool endpoint is not defined",
)
@pytest.mark.asyncio
async def test_azure_container_code_executor_timeout() -> None:
    assert POOL_ENDPOINT is not None
    cancellation_token = CancellationToken()
    executor = ACADynamicSessionsCodeExecutor(
        pool_management_endpoint=POOL_ENDPOINT, credential=DefaultAzureCredential(), timeout=1
    )
    await executor.start()
    code_blocks = [CodeBlock(code="import time; time.sleep(10); print('hello world!')", language="python")]
    with pytest.raises(asyncio.TimeoutError):
        await executor.execute_code_blocks(code_blocks, cancellation_token)
    await executor.stop()


@pytest.mark.skipif(
    not POOL_ENDPOINT,
    reason="do not run if pool endpoint is not defined",
)
@pytest.mark.asyncio
async def test_azure_container_code_executor_cancellation() -> None:
    assert POOL_ENDPOINT is not None
    cancellation_token = CancellationToken()
    executor = ACADynamicSessionsCodeExecutor(
        pool_management_endpoint=POOL_ENDPOINT, credential=DefaultAzureCredential()
    )
    await executor.start()
    code_blocks = [CodeBlock(code="import time; time.sleep(10); print('hello world!')", language="python")]

    coro = executor.execute_code_blocks(code_blocks, cancellation_token)

    await asyncio.sleep(1)
    cancellation_token.cancel()

    with pytest.raises(asyncio.CancelledError):
        await coro
    await executor.stop()


@pytest.mark.skipif(
    not POOL_ENDPOINT,
    reason="do not run if pool endpoint is not defined",
)
@pytest.mark.asyncio
async def test_upload_files() -> None:
    assert POOL_ENDPOINT is not None
    test_file_1 = "test1.txt"
    test_file_1_contents = "test file 1"
    test_file_2 = "test2"
    test_file_2_contents = "test file 2"
    cancellation_token = CancellationToken()

    with tempfile.TemporaryDirectory() as temp_dir:
        executor = ACADynamicSessionsCodeExecutor(
            pool_management_endpoint=POOL_ENDPOINT, credential=DefaultAzureCredential(), work_dir=temp_dir
        )
        await executor.start()

        async with await open_file(os.path.join(temp_dir, test_file_1), "w") as f:
            await f.write(test_file_1_contents)
        async with await open_file(os.path.join(temp_dir, test_file_2), "w") as f:
            await f.write(test_file_2_contents)

        await executor.upload_files([test_file_1, test_file_2], cancellation_token)

    file_list = await executor.get_file_list(cancellation_token)
    assert test_file_1 in file_list
    assert test_file_2 in file_list

    code_blocks = [
        CodeBlock(
            code=f"""
with open("{test_file_1}") as f:
    print(f.read())
with open("{test_file_2}") as f:
    print(f.read())
""",
            language="python",
        )
    ]
    code_result = await executor.execute_code_blocks(code_blocks, cancellation_token)
    assert code_result.exit_code == 0
    assert test_file_1_contents in code_result.output
    assert test_file_2_contents in code_result.output

    await executor.stop()


@pytest.mark.skipif(
    not POOL_ENDPOINT,
    reason="do not run if pool endpoint is not defined",
)
@pytest.mark.asyncio
async def test_download_files() -> None:
    assert POOL_ENDPOINT is not None
    test_file_1 = "test1.txt"
    test_file_1_contents = "azure test file 1"
    test_file_2 = "test2"
    test_file_2_contents = "azure test file 2"
    cancellation_token = CancellationToken()

    with tempfile.TemporaryDirectory() as temp_dir:
        executor = ACADynamicSessionsCodeExecutor(
            pool_management_endpoint=POOL_ENDPOINT, credential=DefaultAzureCredential(), work_dir=temp_dir
        )
        await executor.start()

        code_blocks = [
            CodeBlock(
                code=f"""
with open("{test_file_1}", "w") as f:
    f.write("{test_file_1_contents}")
with open("{test_file_2}", "w") as f:
    f.write("{test_file_2_contents}")
""",
                language="python",
            ),
        ]
        code_result = await executor.execute_code_blocks(code_blocks, cancellation_token)
        assert code_result.exit_code == 0

        file_list = await executor.get_file_list(cancellation_token)
        assert test_file_1 in file_list
        assert test_file_2 in file_list

        await executor.download_files([test_file_1, test_file_2], cancellation_token)

        assert os.path.isfile(os.path.join(temp_dir, test_file_1))
        async with await open_file(os.path.join(temp_dir, test_file_1), "r") as f:
            content = await f.read()
            assert test_file_1_contents in content
        assert os.path.isfile(os.path.join(temp_dir, test_file_2))
        async with await open_file(os.path.join(temp_dir, test_file_2), "r") as f:
            content = await f.read()
            assert test_file_2_contents in content

        await executor.stop()
