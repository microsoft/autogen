from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_agentchat.agents import CodeExecutorAgent
from autogen_agentchat.ui import Console

from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.agents.file_surfer import FileSurfer
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_ext.agents.magentic_one import MagenticOneCoderAgent
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor


class MagenticOne(MagenticOneGroupChat):
    """
    MagenticOne is a specialized group chat class that integrates various agents
    such as FileSurfer, WebSurfer, Coder, and Executor to provide a comprehensive
    coding and web surfing experience.

    Attributes:
        client (OpenAIChatCompletionClient): The client used for model interactions.

    Example:
        .. code-block:: python

            import asyncio
            from autogen_ext.models.openai import OpenAIChatCompletionClient
            from autogen_ext.teams import MagenticOne
            from autogen_agentchat.ui import Console


            async def example_usage():
                client = OpenAIChatCompletionClient(model="gpt-4o")
                m1 = MagenticOne(client=client)
                task = "Write a Python script to fetch data from an API."
                result = await Console(m1.run_stream(task=task))
                print(result)


            if __name__ == "__main__":
                asyncio.run(example_usage())
    """

    def __init__(self, client: OpenAIChatCompletionClient):
        """
        Initializes the MagenticOne group chat with the provided client and sets up
        the agents: FileSurfer, WebSurfer, Coder, and Executor.

        Args:
            client (OpenAIChatCompletionClient): The client used for model interactions.
        """
        self.client = client
        fs = FileSurfer("FileSurfer", model_client=client)
        ws = MultimodalWebSurfer("WebSurfer", model_client=client)
        coder = MagenticOneCoderAgent("Coder", model_client=client)
        executor = CodeExecutorAgent("Executor", code_executor=LocalCommandLineCodeExecutor())
        super().__init__([fs, ws, coder, executor], model_client=client)
