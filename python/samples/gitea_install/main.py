from dotenv import load_dotenv
load_dotenv("./.env")

import os
import asyncio
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent, CodeExecutorAgent
from autogen_agentchat.conditions import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import AzureOpenAIChatCompletionClient
from autogen_ext.agents.web_surfer import MultimodalWebSurfer
from pathlib import Path
from autogen_ext.code_executors.local import LocalCommandLineCodeExecutor
 
async def main() -> None:
    model_client = AzureOpenAIChatCompletionClient(
        model=os.getenv("model"),
        azure_endpoint=os.getenv("AZURE_API_BASE"),
        api_key=os.getenv("AZURE_API_KEY"),
        api_version=os.getenv("AZURE_API_VERSION")
    )
    task = "Install Gitea on Kubernetes using Helm. Install to the gitea namespace. Assume kubectl and Helm are pre-configured in the local environment."
    
    work_dir = Path("coding")
    work_dir.mkdir(exist_ok=True)
    local_executor = LocalCommandLineCodeExecutor(timeout=120, work_dir=work_dir)
    code_executor_agent = CodeExecutorAgent("code_executor", code_executor=local_executor)
    
    assistant = AssistantAgent(
        name="assistant", 
        model_client=model_client,
        #tools=[local_executor], #Unsupported by AssistantAgent class
        system_message="Use the code_executor_agent to solve tasks."
        )
    web_surfer = MultimodalWebSurfer("web_surfer", model_client)
    user_proxy = UserProxyAgent("user_proxy")
    termination = TextMentionTermination("exit") # Type 'exit' to end the conversation.
    #team = RoundRobinGroupChat([web_surfer, assistant, user_proxy, code_executor_agent], termination_condition=termination)
    team = RoundRobinGroupChat([assistant, user_proxy, code_executor_agent], termination_condition=termination) #assistant seems capable of web searches
    await Console(team.run_stream(task=task))
    
asyncio.run(main())
