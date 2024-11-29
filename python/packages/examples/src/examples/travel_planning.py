from autogen_agentchat.agents import CodingAssistantAgent
from autogen_agentchat.task import TextMentionTermination
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models import OpenAIChatCompletionClient

from exts.agents.llama_index_agent import LlamaIndexAgent,LLamaAssistantAgent
from llama_index.llms.ollama import Ollama
from llama_index.core.agent import ReActAgent
from llama_index.agent.openai import OpenAIAgent
from llama_index.core.memory import ChatSummaryMemoryBuffer
from llama_index.llms.openai_like import OpenAILike
#llm = Ollama(model="qwen2.5:14b-instruct-q4_K_M", api_key="fake")
llm = OpenAILike(api_base="http://127.0.0.1:4000",model='gpt-4o', api_key="fake",is_function_calling_model=True,is_chat_model=True)
planner_agent = LlamaIndexAgent(description="A helpful assistant that can plan trips.",
            llama_index_agent=OpenAIAgent.from_tools(
                system_prompt='You are a helpful assistant that can suggest a travel plan for a user based on their request.',
                tools=[],
                llm=llm,
                max_iterations=8,
                memory=ChatSummaryMemoryBuffer(llm=llm, token_limit=16000),
                verbose=True,
            )
        )


planner_agent = LLamaAssistantAgent(
    name="planner_agent",
    llama_index_agent=OpenAIAgent.from_tools(
                system_prompt='You are a helpful assistant that can suggest a travel plan for a user based on their request.',
                tools=[],
                llm=llm,
                max_iterations=8,
                memory=ChatSummaryMemoryBuffer(llm=llm, token_limit=16000),
                verbose=True,
            ),
    description="A helpful assistant that can plan trips."
)

local_agent = LLamaAssistantAgent(
    "local_agent",
    llama_index_agent=OpenAIAgent.from_tools(
                system_prompt='You are a helpful assistant that can suggest authentic and interesting local activities or places to visit for a user and can utilize any context information provided.',
                tools=[],
                llm=llm,
                max_iterations=8,
                memory=ChatSummaryMemoryBuffer(llm=llm, token_limit=16000),
                verbose=True,
            ),
    description="A local assistant that can suggest local activities or places to visit.",
)

language_agent = LLamaAssistantAgent(
    "language_agent",
    llama_index_agent=OpenAIAgent.from_tools(
                system_prompt='You are a helpful assistant that can review travel plans, providing feedback on important/critical tips about how best to address language or communication challenges for the given destination. If the plan already includes language tips, you can mention that the plan is satisfactory, with rationale.',
                tools=[],
                llm=llm,
                max_iterations=8,
                memory=ChatSummaryMemoryBuffer(llm=llm, token_limit=16000),
                verbose=True,
            ),
    description="A helpful assistant that can provide language tips for a given destination.",
)

travel_summary_agent = LLamaAssistantAgent(
    "travel_summary_agent",
    llama_index_agent=OpenAIAgent.from_tools(
                system_prompt='You are a helpful assistant that can take in all of the suggestions and advice from the other agents and provide a detailed tfinal travel plan. You must ensure th b at the final plan is integrated and complete. YOUR FINAL RESPONSE MUST BE THE COMPLETE PLAN. When the plan is complete and all perspectives are integrated, you can respond with TERMINATE.',
                tools=[],
                llm=llm,
                max_iterations=8,
                memory=ChatSummaryMemoryBuffer(llm=llm, token_limit=16000),
                verbose=True,
            ),
    description="A helpful assistant that can summarize the travel plan.",
)

async def main():
    termination = TextMentionTermination("TERMINATE")
    group_chat = RoundRobinGroupChat(
        [planner_agent, local_agent, language_agent, travel_summary_agent], termination_condition=termination
    )
    result = await group_chat.run(task="Plan a 3 day trip to Nepal.")
    print(result)

import asyncio
if __name__ == "__main__":
    asyncio.run(main())

