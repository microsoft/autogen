import warnings
from typing import Awaitable, Callable, List, Optional, Union

from autogen_agentchat.agents import CodeExecutorAgent, UserProxyAgent
from autogen_agentchat.base import ChatAgent
from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_core import CancellationToken
from autogen_core.code_executor import CodeExecutor
from autogen_core.models import ChatCompletionClient

from autogen_ext.agents.file_surfer import FileSurfer
from autogen_ext.agents.magentic_one import MagenticOneCoderAgent, MagenticOneComputerTerminalAgent
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.models.openai._openai_client import BaseOpenAIChatCompletionClient

# Docker imports for default code executor
try:
    import docker
    from docker.errors import DockerException

    from autogen_ext.code_executors.docker import DockerCommandLineCodeExecutor

    _docker_available = True
except ImportError:
    docker = None  # type: ignore
    DockerException = Exception  # type: ignore
    DockerCommandLineCodeExecutor = None  # type: ignore
    _docker_available = False

SyncInputFunc = Callable[[str], str]
AsyncInputFunc = Callable[[str, Optional[CancellationToken]], Awaitable[str]]
InputFuncType = Union[SyncInputFunc, AsyncInputFunc]


def _is_docker_available() -> bool:
    """Check if Docker is available and running."""
    if not _docker_available:
        return False

    try:
        if docker is not None:
            client = docker.from_env()
            client.ping()  # type: ignore
            return True
    except DockerException:
        return False

    return False


def _create_default_code_executor() -> CodeExecutor:
    """Create the default code executor, preferring Docker if available."""
    if _is_docker_available() and DockerCommandLineCodeExecutor is not None:
        try:
            return DockerCommandLineCodeExecutor()
        except Exception:
            # Fallback to local if Docker fails to initialize
            pass

    # Issue warning and use local executor if Docker is not available
    warnings.warn(
        "Docker is not available or not running. Using LocalCommandLineCodeExecutor instead of the recommended DockerCommandLineCodeExecutor. "
        "For security, it is recommended to install Docker and ensure it's running before using MagenticOne. "
        "To install Docker, visit: https://docs.docker.com/get-docker/",
        UserWarning,
        stacklevel=3,
    )
    return LocalCommandLineCodeExecutor()


class MagenticOne(MagenticOneGroupChat):
    """
    MagenticOne is a specialized group chat class that integrates various agents
    such as FileSurfer, WebSurfer, Coder, and Executor to solve complex tasks.
    To read more about the science behind Magentic-One, see the full blog post: `Magentic-One: A Generalist Multi-Agent System for Solving Complex Tasks <https://www.microsoft.com/en-us/research/articles/magentic-one-a-generalist-multi-agent-system-for-solving-complex-tasks>`_ and the references below.

    Installation:

    .. code-block:: bash

        pip install "autogen-ext[magentic-one]"


    Args:
        client (ChatCompletionClient): The client used for model interactions.
        hil_mode (bool): Optional; If set to True, adds the UserProxyAgent to the list of agents.

    .. warning::
        Using Magentic-One involves interacting with a digital world designed for humans, which carries inherent risks. To minimize these risks, consider the following precautions:

        1. **Use Containers**: Run all tasks in docker containers to isolate the agents and prevent direct system attacks.
        2. **Virtual Environment**: Use a virtual environment to run the agents and prevent them from accessing sensitive data.
        3. **Monitor Logs**: Closely monitor logs during and after execution to detect and mitigate risky behavior.
        4. **Human Oversight**: Run the examples with a human in the loop to supervise the agents and prevent unintended consequences.
        5. **Limit Access**: Restrict the agents' access to the internet and other resources to prevent unauthorized actions.
        6. **Safeguard Data**: Ensure that the agents do not have access to sensitive data or resources that could be compromised. Do not share sensitive information with the agents.

        Be aware that agents may occasionally attempt risky actions, such as recruiting humans for help or accepting cookie agreements without human involvement. Always ensure agents are monitored and operate within a controlled environment to prevent unintended consequences. Moreover, be cautious that Magentic-One may be susceptible to prompt injection attacks from webpages.

    Architecture:

    Magentic-One is a generalist multi-agent system for solving open-ended web and file-based tasks across a variety of domains. It represents a significant step towards developing agents that can complete tasks that people encounter in their work and personal lives.

    Magentic-One work is based on a multi-agent architecture where a lead Orchestrator agent is responsible for high-level planning, directing other agents, and tracking task progress. The Orchestrator begins by creating a plan to tackle the task, gathering needed facts and educated guesses in a Task Ledger that is maintained. At each step of its plan, the Orchestrator creates a Progress Ledger where it self-reflects on task progress and checks whether the task is completed. If the task is not yet completed, it assigns one of Magentic-One's other agents a subtask to complete. After the assigned agent completes its subtask, the Orchestrator updates the Progress Ledger and continues in this way until the task is complete. If the Orchestrator finds that progress is not being made for enough steps, it can update the Task Ledger and create a new plan.

    Overall, Magentic-One consists of the following agents:

    - Orchestrator: The lead agent responsible for task decomposition and planning, directing other agents in executing subtasks, tracking overall progress, and taking corrective actions as needed.
    - WebSurfer: An LLM-based agent proficient in commanding and managing the state of a Chromium-based web browser. It performs actions on the browser and reports on the new state of the web page.
    - FileSurfer: An LLM-based agent that commands a markdown-based file preview application to read local files of most types. It can also perform common navigation tasks such as listing the contents of directories and navigating a folder structure.
    - Coder: An LLM-based agent specialized in writing code, analyzing information collected from other agents, or creating new artifacts.
    - ComputerTerminal: Provides the team with access to a console shell where the Coder's programs can be executed, and where new programming libraries can be installed.

    Together, Magentic-One's agents provide the Orchestrator with the tools and capabilities needed to solve a broad variety of open-ended problems, as well as the ability to autonomously adapt to, and act in, dynamic and ever-changing web and file-system environments.

    Examples:

        .. code-block:: python

            # Autonomously complete a coding task:
            import asyncio
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_ext.teams.magentic_one import MagenticOne
            from autogen_agentchat.ui import Console


            async def example_usage():
                client = OpenAIChatCompletionClient(model="gpt-4o")
                m1 = MagenticOne(client=client)  # Uses DockerCommandLineCodeExecutor by default
                task = "Write a Python script to fetch data from an API."
                result = await Console(m1.run_stream(task=task))
                print(result)


            if __name__ == "__main__":
                asyncio.run(example_usage())


        .. code-block:: python

            # Enable human-in-the-loop mode with explicit Docker executor
            import asyncio
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_ext.teams.magentic_one import MagenticOne
            from autogen_ext.code_executors.docker import DockerCommandLineCodeExecutor
            from autogen_agentchat.ui import Console


            async def example_usage_hil():
                client = OpenAIChatCompletionClient(model="gpt-4o")
                # Explicitly specify Docker code executor for better security
                async with DockerCommandLineCodeExecutor() as code_executor:
                    m1 = MagenticOne(client=client, hil_mode=True, code_executor=code_executor)
                    task = "Write a Python script to fetch data from an API."
                    result = await Console(m1.run_stream(task=task))
                    print(result)


            if __name__ == "__main__":
                asyncio.run(example_usage_hil())

    References:
        .. code-block:: bibtex

            @article{fourney2024magentic,
                title={Magentic-one: A generalist multi-agent system for solving complex tasks},
                author={Fourney, Adam and Bansal, Gagan and Mozannar, Hussein and Tan, Cheng and Salinas, Eduardo and Niedtner, Friederike and Proebsting, Grace and Bassman, Griffin and Gerrits, Jack and Alber, Jacob and others},
                journal={arXiv preprint arXiv:2411.04468},
                year={2024},
                url={https://arxiv.org/abs/2411.04468}
            }


    """

    def __init__(
        self,
        client: ChatCompletionClient,
        hil_mode: bool = False,
        input_func: InputFuncType | None = None,
        code_executor: CodeExecutor | None = None,
    ):
        self.client = client
        self._validate_client_capabilities(client)

        if code_executor is None:
            warnings.warn(
                "Instantiating MagenticOne without a code_executor is deprecated. Provide a code_executor to clear this warning (e.g., code_executor=DockerCommandLineCodeExecutor() ).",
                DeprecationWarning,
                stacklevel=2,
            )
            code_executor = _create_default_code_executor()

        fs = FileSurfer("FileSurfer", model_client=client)
        ws = MultimodalWebSurfer("WebSurfer", model_client=client)
        coder = MagenticOneCoderAgent("Coder", model_client=client)
        executor = MagenticOneComputerTerminalAgent("ComputerTerminal", model_client=client, code_executor=code_executor)

        agents: List[ChatAgent] = [fs, ws, coder, executor]
        if hil_mode:
            user_proxy = UserProxyAgent("User", input_func=input_func)
            agents.append(user_proxy)
        super().__init__(agents, model_client=client)

    def _validate_client_capabilities(self, client: ChatCompletionClient) -> None:
        capabilities = client.model_info
        required_capabilities = ["function_calling", "json_output"]

        if not all(capabilities.get(cap) for cap in required_capabilities):
            warnings.warn(
                "Client capabilities for MagenticOne must include vision, " "function calling, and json output.",
                stacklevel=2,
            )

        if not isinstance(client, BaseOpenAIChatCompletionClient):
            warnings.warn(
                "MagenticOne performs best with OpenAI GPT-4o model either " "through OpenAI or Azure OpenAI.",
                stacklevel=2,
            )
