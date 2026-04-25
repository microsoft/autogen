import asyncio
from typing import Literal
from pydantic import BaseModel
from autogen_agentchat.agents import AssistantAgent
from autogen_agentchat.messages import StructuredMessage
from autogen_agentchat.ui import Console
from autogen_ext.models.openai import OpenAIChatCompletionClient

# The response format for the agent as a Pydantic base model.
class AgentResponse(BaseModel):
    thoughts: str
    response: Literal["happy", "sad", "neutral"]

async def main():
    # Create an agent that uses the OpenAI GPT-4o model.
    model_client = OpenAIChatCompletionClient(model="gpt-4o")
    agent = AssistantAgent(
        "assistant",
        model_client=model_client,
        system_message="Categorize the input as happy, sad, or neutral following the JSON format.",
        # Define the output content type of the agent.
        output_content_type=AgentResponse,
    )
    result = await Console(agent.run_stream(task="I am happy."))
    # Check the last message in the result, validate its type, and print the thoughts and response.
    assert isinstance(result.messages[-1], StructuredMessage)
    assert isinstance(result.messages[-1].content, AgentResponse)
    print("Thought: ", result.messages[-1].content.thoughts)
    print("Response: ", result.messages[-1].content.response)
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(main())
