import json
from queue import Empty
from typing import List

from jupyter_client import KernelManager
from jupyter_client.kernelspec import NoSuchKernel, KernelSpecManager
from pydantic import BaseModel, Field
from autogen.code_utils import DEFAULT_TIMEOUT
from autogen.coding.base import CodeBlock, CodeExtractor, CodeResult
from autogen.coding.markdown_code_extractor import MarkdownCodeExtractor


class IPythonCodeExecutor(BaseModel):
    """A code executor class that executes code statefully using IPython kernel.

    Each execution is stateful and can access variables created from previous
    executions in the same session.
    """

    class UserCapability:
        """An AgentCapability class that gives agent ability use a stateful
        code executor."""

        DEFAULT_SYSTEM_MESSAGE_UPDATE = """You have been given coding capability
to solve tasks using Python code in a stateful IPython kernel.
When you write Python code, put the code in a markdown code block with the language set to Python.
For example:
```python
x = 3
```
You can use the variable `x` in subsequent code blocks.
```python
print(x)
```
The output may be text, a table, or an image.
When you suggest code, always write incrementally rather than all at once.
For example, if you want to import a library, do it in a separate code block.
If you want to define a function or a class, do it in a separate code block.
Leverage the statefulness of the kernel to avoid repeating code.
"""

        def add_to_agent(self, agent):
            """Add this capability to an agent."""
            agent.update_system_message(agent.system_message + self.DEFAULT_SYSTEM_MESSAGE_UPDATE)

    timeout: int = Field(default=DEFAULT_TIMEOUT, ge=1)
    kernel: str = "python3"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Check if the kernel is installed.
        if self.kernel not in KernelSpecManager().find_kernel_specs():
            raise ValueError(
                f"Kernel {self.kernel} is not installed. "
                "Please first install it with "
                f"`python -m ipykernel install --user --name {self.kernel}`."
            )
        self._kernel_manager = KernelManager()
        self._kernel_manager.start_kernel()
        self._kernel_client = self._kernel_manager.client()
        self._kernel_client.start_channels()
        self._timeout = self.timeout

    @property
    def user_capability(self) -> "IPythonCodeExecutor.UserCapability":
        """Export a user capability that can be added to an agent."""
        return IPythonCodeExecutor.UserCapability()

    @property
    def code_extractor(self) -> CodeExtractor:
        """Export a code extractor that can be used by an agent."""
        return MarkdownCodeExtractor()

    def execute_code_blocks(self, code_blocks: List[CodeBlock]) -> CodeResult:
        self._kernel_client.wait_for_ready()
        outputs = []
        for code_block in code_blocks:
            self._kernel_client.execute(code_block.code, store_history=True)
            while True:
                try:
                    msg = self._kernel_client.get_iopub_msg(timeout=self._timeout)
                    msg_type = msg["msg_type"]
                    content = msg["content"]
                    if msg_type in ["execute_result", "display_data"]:
                        # Output is data.
                        outputs.append(json.dumps(content["data"]))
                    elif msg_type == "stream":
                        # Output is a text.
                        outputs.append(content["text"])
                    elif msg_type == "error":
                        # Output is an error.
                        return CodeResult(
                            exit_code=1,
                            output=f"ERROR: {content['ename']}: {content['evalue']}\n{content['traceback']}",
                        )
                    if msg_type == "status" and content["execution_state"] == "idle":
                        break
                # handle time outs.
                except Empty:
                    return CodeResult(
                        exit_code=1,
                        output=f"ERROR: Timeout waiting for output from code block: {code_block.code}",
                    )
        # We return the full output.
        return CodeResult(exit_code=0, output="".join([str(output) for output in outputs]))

    def reset(self) -> None:
        """Restart a new session."""
        self._kernel_client.stop_channels()
        self._kernel_client.start_channels()
