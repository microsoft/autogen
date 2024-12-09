from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.task import Console, TextMentionTermination,HandoffTermination,StopMessageTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_agentchat.teams import Swarm
from autogen_ext.models import OpenAIChatCompletionClient
from exts.agents.llama_index_agentchat import LlamaIndexAssistantAgent

from llama_index.core.callbacks import CallbackManager
from langfuse.llama_index import LlamaIndexCallbackHandler
from llama_index.llms.openai_like import OpenAILike

langfuse_callback_handler = LlamaIndexCallbackHandler(
    public_key="pk-lf-05e5e78f-dffc-43ef-93ae-cf3c885d695b",
    secret_key="sk-lf-7838d833-99dc-4eb7-9955-4f8cce5e0db1",
    host="http://127.0.0.1:13001"
)
from llama_index.core import Settings
Settings.callback_manager = CallbackManager([langfuse_callback_handler])
llm = OpenAILike(model="qwen2.5:14b-instruct-q4_K_M",is_chat_model=True,is_function_calling_model=False,
                 api_base="http://127.0.0.1:11434/v1",api_key="fake",temperature=0.3,max_tokens=200)
# Define a tool
async def get_weather(city: str) -> str:
    return f"The weather in {city} is 73 degrees and Sunny."

import asyncio
from typing import List, Sequence

from autogen_agentchat.agents import BaseChatAgent
from autogen_agentchat.base import Response
from autogen_agentchat.messages import ChatMessage
from autogen_core.base import CancellationToken
from autogen_agentchat.messages import AgentMessage, ChatMessage, TextMessage
from exts.agents.user_agent import UserProxyAgent
from llama_index.core.agent import ReActAgent
from llama_index.core.agent.react.formatter import ReActChatFormatter
from llama_index.core.callbacks import (
    trace_method,
)

async def main() -> None:
    # Define an agent
    weather_agent = LlamaIndexAssistantAgent(
        name="weather_agent",
        llm=llm,
        max_func_calls=10,
        handoffs=["user"],
        callbackManager=Settings.callback_manager,
        system_message="当任务完成后请回复TERMINATE",
       
        tools=[get_weather],
    )

    # Define termination condition
    termination = TextMentionTermination("TERMINATE")| StopMessageTermination()

    # Define a team
    agent_team = Swarm([weather_agent,UserProxyAgent("user")], termination_condition=termination)

    # Run the team and stream messages to the console
    stream = agent_team.run_stream(task="今天温度是多少")
    await Console(stream)

system_message="""
请记住下面两点要求：
1. 在解决问题过程中，如果你需要向用户获取更详细的信息，可以handoff到user。
2. 如果你觉得任务完成了，请回复TERMINATE
"""

from exts.agents.llama_index_agent_runner import LlamaIndexAssistantAgentRunner

class MyTask:
    def __init__(self,callbackManager:CallbackManager) -> None:
        self.callback_manager = callbackManager

        self.weather_agent = LlamaIndexAssistantAgentRunner(
            name="weather_agent",
            handoffs=["user"],
            tools=[get_weather],
            factory=lambda llama_tools: ReActAgent.from_tools(llm=llm,tools=llama_tools,
                                                            react_chat_formatter=ReActChatFormatter.from_defaults(context=system_message)
                                                            ,max_iterations=10,callback_manager=Settings.callback_manager))
         # Define termination condition
        termination = TextMentionTermination("TERMINATE")| StopMessageTermination()
        self.agent_team = Swarm([self.weather_agent,UserProxyAgent("user")], termination_condition=termination)

    @trace_method("team")
    async def main_agent_runner(self,task:str) -> None:
        # Run the team and stream messages to the console
        stream = self.agent_team.run_stream(task=task)
        await Console(stream)

    



# NOTE: if running this inside a Python script you'll need to use asyncio.run(main()).
import asyncio

mt = MyTask(Settings.callback_manager)
asyncio.run(mt.main_agent_runner('今天温度是多少'))