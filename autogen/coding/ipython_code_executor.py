from __future__ import annotations
from queue import Empty
from typing import List

from pydantic import BaseModel, Field
from autogen.code_utils import DEFAULT_TIMEOUT, extract_code

from autogen.coding.base import CodeBlock, CodeResult

try:
    from termcolor import colored
except ImportError:

    def colored(x, *args, **kwargs):
        return x


from nbformat.v4 import new_output
from jupyter_client import KernelManager


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
When you write Python code, put the code in a block with the language set to Python.
For example:
```python
x = 3
print(x)
```
The code will be executed in a IPython kernel, and the output will be returned to you.
You can use variables created earlier in the subsequent code blocks.
"""

        def add_to_agent(self, agent):
            """Add this capability to an agent."""
            agent.update_system_message(agent.system_message + self.DEFAULT_SYSTEM_MESSAGE_UPDATE)

    timeout: int = Field(default=DEFAULT_TIMEOUT, ge=1)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._kernel_manager = KernelManager()
        self._kernel_client = self._kernel_manager.client()
        self._kernel_client.start_channels()
        self._timeout = self.timeout

    @property
    def user_capability(self) -> IPythonCodeExecutor.UserCapability:
        """Export a user capability that can be added to an agent."""
        return IPythonCodeExecutor.UserCapability()

    def extract_code_blocks(self, message: str) -> List[CodeBlock]:
        """Extract IPython code blocks from a message.

        Args:
            message (str): The message to extract code blocks from.

        Returns:
            List[CodeBlock]: The extracted code blocks.
        """
        code_blocks = []
        for lang, code in extract_code(message):
            code_blocks.append(CodeBlock(code=code, language=lang))
        return code_blocks

    def execute_code_blocks(self, code_blocks: List[CodeBlock]) -> CodeResult:
        outputs = []
        for code_block in code_blocks:
            self._kernel_client.execute(code_block.code, store_history=True)
            while True:
                try:
                    msg = self.kernel_client.get_iopub_msg(timeout=self._timeout)
                    msg_type = msg["msg_type"]
                    content = msg["content"]
                    if msg_type in ["execute_result", "display_data"]:
                        # Check if the output is an image
                        if "image/png" in content["data"]:
                            # Replace image with a note
                            note = "Image output has been replaced with this note."
                            outputs.append(new_output(msg_type, data={"text/plain": note}))
                        else:
                            outputs.append(new_output(msg_type, data=content["data"]))
                    elif msg_type == "stream":
                        outputs.append(new_output(msg_type, name=content["name"], text=content["text"]))
                    elif msg_type == "error":
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
