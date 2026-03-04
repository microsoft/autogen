# User-Defined Functions in Code Executors

You can expose Python helper functions to command-line code executors, then import and call them from generated code blocks.

This works with both:

- {py:class}`~autogen_ext.code_executors.local.LocalCommandLineCodeExecutor`
- {py:class}`~autogen_ext.code_executors.docker.DockerCommandLineCodeExecutor`

## Basic Usage

Pass a list of Python callables through the `functions` argument.

```python
import asyncio
import tempfile

from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor


def add_two_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


async def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        executor = LocalCommandLineCodeExecutor(
            work_dir=temp_dir,
            functions=[add_two_numbers],
        )
        await executor.start()

        code = f"""from {executor.functions_module} import add_two_numbers
print(add_two_numbers(1, 2))"""

        result = await executor.execute_code_blocks(
            code_blocks=[CodeBlock(language="python", code=code)],
            cancellation_token=CancellationToken(),
        )
        print(result.output)  # 3
        await executor.stop()


asyncio.run(main())
```

## Add Package and Import Requirements

Use {py:func}`~autogen_core.code_executor.with_requirements` when a function depends on external packages or imports.

```python
import asyncio
import tempfile

import polars
from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock, with_requirements
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor


@with_requirements(
    python_packages=["polars"],
    global_imports=["polars"],
)
def load_data() -> polars.DataFrame:
    return polars.DataFrame({"name": ["John", "Anna"]})


async def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        executor = LocalCommandLineCodeExecutor(work_dir=temp_dir, functions=[load_data])
        await executor.start()

        code = f"""from {executor.functions_module} import load_data
data = load_data()
print(data["name"][0])"""

        result = await executor.execute_code_blocks(
            code_blocks=[CodeBlock(language="python", code=code)],
            cancellation_token=CancellationToken(),
        )
        print(result.output)  # John
        await executor.stop()


asyncio.run(main())
```

When requirements are provided, the executor installs required packages before running code blocks.

## Custom Module Name

By default, functions are written to a generated module named `functions`.
You can customize it with `functions_module`:

```python
executor = LocalCommandLineCodeExecutor(
    work_dir=temp_dir,
    functions=[add_two_numbers],
    functions_module="math_helpers",
)
```

Then import from that module inside generated code:

```python
from math_helpers import add_two_numbers
```

`functions_module` must be a valid Python identifier.

## String-Defined Functions

If functions are assembled dynamically, use
{py:meth}`~autogen_core.code_executor.FunctionWithRequirements.from_str`.

```python
from autogen_core.code_executor import FunctionWithRequirements

func = FunctionWithRequirements.from_str(
    """
def add_two_numbers(a: int, b: int) -> int:
    \"\"\"Add two numbers together.\"\"\"
    return a + b
"""
)
```

Then pass `func` in the same `functions=[...]` list.

## Use with Docker Executor

The usage pattern is the same for Docker:

```python
import asyncio
from pathlib import Path

from autogen_core import CancellationToken
from autogen_core.code_executor import CodeBlock
from autogen_ext.code_executors.docker import DockerCommandLineCodeExecutor


def add_two_numbers(a: int, b: int) -> int:
    return a + b


async def main() -> None:
    async with DockerCommandLineCodeExecutor(
        work_dir=Path("coding"),
        functions=[add_two_numbers],
    ) as executor:
        code = f"""from {executor.functions_module} import add_two_numbers
print(add_two_numbers(2, 5))"""
        result = await executor.execute_code_blocks(
            code_blocks=[CodeBlock(language="python", code=code)],
            cancellation_token=CancellationToken(),
        )
        print(result.output)  # 7


asyncio.run(main())
```

## Troubleshooting

- If imports in `global_imports` are invalid, setup fails with a `ValueError`.
- If a package in `python_packages` cannot be installed, setup fails with a `ValueError`.
- If `functions_module` is not a valid identifier, constructor initialization fails.
