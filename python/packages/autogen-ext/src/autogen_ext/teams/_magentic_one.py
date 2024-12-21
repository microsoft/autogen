from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_agentchat.agents import CodeExecutorAgent
from autogen_agentchat.ui import Console

from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.agents.file_surfer import FileSurfer
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_ext.agents.magentic_one import MagenticOneCoderAgent
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor


class MagenticOne:
    def __init__(self, client: OpenAIChatCompletionClient):
        self.client = client
        self.fs = FileSurfer("FileSurfer", model_client=client)
        self.ws = MultimodalWebSurfer("WebSurfer", model_client=client)
        self.coder = MagenticOneCoderAgent("Coder", model_client=client)
        self.executor = CodeExecutorAgent("Executor", code_executor=LocalCommandLineCodeExecutor())
        self.team = MagenticOneGroupChat([self.fs, self.ws, self.coder, self.executor], model_client=client)

    async def run(self, task: str):
        return await Console(self.team.run_stream(task=task))
