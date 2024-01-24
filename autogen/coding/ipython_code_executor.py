from __future__ import annotations
from queue import Empty
from typing import Dict, Tuple
import warnings

from autogen.coding.base import CodeBlock, CodeResult

try:
    from termcolor import colored
except ImportError:

    def colored(x, *args, **kwargs):
        return x


from nbformat.v4 import new_output
from jupyter_client import KernelManager


class IPythonCodeExecutor:
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

    def __init__(self, code_execution_config: Dict):
        self._code_execution_config = code_execution_config.copy()
        self._kernel_manager = KernelManager(kernel_name="python3")
        self._kernel_client = self._kernel_manager.client()
        self._kernel_client.start_channels()
        self._timeout = self._code_execution_config.get("timeout", 60)

    @property
    def user_capability(self) -> IPythonCodeExecutor.UserCapability:
        """Export a user capability that can be added to an agent."""
        return IPythonCodeExecutor.UserCapability()

    @property
    def code_execution_config(self) -> Dict:
        """Return the code execution config."""
        return self._code_execution_config

    def execute_code(self, code_block: CodeBlock, **kwargs) -> CodeResult:
        self._kernel_client.execute(code_block.code, store_history=True)
        outputs = []
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
                        docker_image_name=None,
                    )
                if msg_type == "status" and content["execution_state"] == "idle":
                    break
            # handle time outs.
            except Empty:
                return CodeResult(
                    exit_code=1,
                    output=f"ERROR: Timeout waiting for output from code block: {code_block.code}",
                    docker_image_name=None,
                )
        # We return the full output.
        return CodeResult(exit_code=0, output="".join([str(output) for output in outputs]), docker_image_name=None)

    def reset(self) -> None:
        """Restart a new session."""
        self._kernel_client.stop_channels()
        self._kernel_client.start_channels()
