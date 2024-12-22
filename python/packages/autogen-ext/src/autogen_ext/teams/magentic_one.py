from typing import List

from autogen_agentchat.agents import CodeExecutorAgent, UserProxyAgent
from autogen_agentchat.base import ChatAgent
from autogen_agentchat.teams import MagenticOneGroupChat

from autogen_ext.agents.file_surfer import FileSurfer
from autogen_ext.agents.magentic_one import MagenticOneCoderAgent
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
from autogen_ext.models.openai import OpenAIChatCompletionClient


class MagenticOne(MagenticOneGroupChat):
    """
    MagenticOne is a specialized group chat class that integrates various agents
    such as FileSurfer, WebSurfer, Coder, and Executor to provide a comprehensive
    coding and web surfing experience.

    Attributes:
        client (OpenAIChatCompletionClient): The client used for model interactions.
        hil_mode (bool): Optional; If set to True, adds the UserProxyAgent to the list of agents.

    Examples:
        
        .. code-block:: python

            # Autonomously complete a coding task:
            import asyncio
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_ext.teams.magentic_one import MagenticOne
            from autogen_agentchat.ui import Console


            async def example_usage():
                client = OpenAIChatCompletionClient(model="gpt-4o")
                m1 = MagenticOne(client=client)
                task = "Write a Python script to fetch data from an API."
                result = await Console(m1.run_stream(task=task))
                print(result)


            if __name__ == "__main__":
                asyncio.run(example_usage())

    
        .. code-block:: python

            # Enable human-in-the-loop mode        
            import asyncio
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_ext.teams.magentic_one import MagenticOne
            from autogen_agentchat.ui import Console


            async def example_usage_hil():
                client = OpenAIChatCompletionClient(model="gpt-4o")
                # to enable human-in-the-loop mode, set hil_mode=True
                m1 = MagenticOne(client=client, hil_mode=True)
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
                year={2024}
            }
    """

    def __init__(self, client: OpenAIChatCompletionClient, hil_mode: bool = False):
        self.client = client
        fs = FileSurfer("FileSurfer", model_client=client)
        ws = MultimodalWebSurfer("WebSurfer", model_client=client)
        coder = MagenticOneCoderAgent("Coder", model_client=client)
        executor = CodeExecutorAgent("Executor", code_executor=LocalCommandLineCodeExecutor())
        agents: List[ChatAgent] = [fs, ws, coder, executor]
        if hil_mode:
            user_proxy = UserProxyAgent("User")
            agents.append(user_proxy)
        super().__init__(agents, model_client=client)
