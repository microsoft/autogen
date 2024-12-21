from autogen_agentchat.teams import MagenticOneGroupChat
from autogen_agentchat.agents import CodeExecutorAgent
from autogen_agentchat.ui import Console

from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.agents.file_surfer import FileSurfer
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from autogen_ext.agents.magentic_one import MagenticOneCoderAgent
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor


class MagenticOne(MagenticOneGroupChat):
    def __init__(self, client: OpenAIChatCompletionClient):
        self.client = client
        fs = FileSurfer("FileSurfer", model_client=client)
        ws = MultimodalWebSurfer("WebSurfer", model_client=client)
        coder = MagenticOneCoderAgent("Coder", model_client=client)
        executor = CodeExecutorAgent("Executor", code_executor=LocalCommandLineCodeExecutor())
        super().__init__([fs, ws, coder, executor], model_client=client)
