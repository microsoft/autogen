"""
core_sequential_workflow_example.py

Demonstrates a sequential multi-agent workflow in AutoGen:
- ConceptExtractorAgent: Extracts features, audience, USPs
- WriterAgent: Crafts marketing copy
- FormatProofAgent: Polishes and formats copy
- UserAgent: Outputs final result

Agents communicate via publish-subscribe topics in a deterministic sequence.

To run:
    python core_sequential_workflow_example.py

Note: Requires OPENAI_API_KEY in environment for OpenAI examples.
"""
import asyncio
from dataclasses import dataclass

try:
    from autogen_core import (
        MessageContext, RoutedAgent, SingleThreadedAgentRuntime, TopicId, message_handler, type_subscription
    )
    from autogen_core.models import ChatCompletionClient, SystemMessage, UserMessage
    from autogen_ext.models.openai import OpenAIChatCompletionClient
except ImportError as e:
    print("Required packages not installed:", e)
    print("Please install autogen-core and autogen-ext.")
    exit(1)

@dataclass
class Message:
    content: str

concept_extractor_topic_type = "ConceptExtractorAgent"
writer_topic_type = "WriterAgent"
format_proof_topic_type = "FormatProofAgent"
user_topic_type = "User"

@type_subscription(topic_type=concept_extractor_topic_type)
class ConceptExtractorAgent(RoutedAgent):
    def __init__(self, model_client: ChatCompletionClient) -> None:
        super().__init__("A concept extractor agent.")
        self._system_message = SystemMessage(
            content=(
                "You are a marketing analyst. Given a product description, identify:\n"
                "- Key features\n"
                "- Target audience\n"
                "- Unique selling points\n\n"
            )
        )
        self._model_client = model_client

    @message_handler
    async def handle_user_description(self, message: Message, ctx: MessageContext) -> None:
        prompt = f"Product description: {message.content}"
        llm_result = await self._model_client.create(
            messages=[self._system_message, UserMessage(content=prompt, source=self.id.key)],
            cancellation_token=ctx.cancellation_token,
        )
        response = llm_result.content
        assert isinstance(response, str)
        print(f"{'-'*80}\n{self.id.type}:\n{response}")
        await self.publish_message(Message(response), topic_id=TopicId(writer_topic_type, source=self.id.key))

@type_subscription(topic_type=writer_topic_type)
class WriterAgent(RoutedAgent):
    def __init__(self, model_client: ChatCompletionClient) -> None:
        super().__init__("A writer agent.")
        self._system_message = SystemMessage(
            content=(
                "You are a marketing copywriter. Given a block of text describing features, audience, and USPs, "
                "compose a compelling marketing copy (like a newsletter section) that highlights these points. "
                "Output should be short (around 150 words), output just the copy as a single text block."
            )
        )
        self._model_client = model_client

    @message_handler
    async def handle_intermediate_text(self, message: Message, ctx: MessageContext) -> None:
        prompt = f"Below is the info about the product:\n\n{message.content}"
        llm_result = await self._model_client.create(
            messages=[self._system_message, UserMessage(content=prompt, source=self.id.key)],
            cancellation_token=ctx.cancellation_token,
        )
        response = llm_result.content
        assert isinstance(response, str)
        print(f"{'-'*80}\n{self.id.type}:\n{response}")
        await self.publish_message(Message(response), topic_id=TopicId(format_proof_topic_type, source=self.id.key))

@type_subscription(topic_type=format_proof_topic_type)
class FormatProofAgent(RoutedAgent):
    def __init__(self, model_client: ChatCompletionClient) -> None:
        super().__init__("A format & proof agent.")
        self._system_message = SystemMessage(
            content=(
                "You are an editor. Given the draft copy, correct grammar, improve clarity, ensure consistent tone, "
                "give format and make it polished. Output the final improved copy as a single text block."
            )
        )
        self._model_client = model_client

    @message_handler
    async def handle_intermediate_text(self, message: Message, ctx: MessageContext) -> None:
        prompt = f"Draft copy:\n{message.content}."
        llm_result = await self._model_client.create(
            messages=[self._system_message, UserMessage(content=prompt, source=self.id.key)],
            cancellation_token=ctx.cancellation_token,
        )
        response = llm_result.content
        assert isinstance(response, str)
        print(f"{'-'*80}\n{self.id.type}:\n{response}")
        await self.publish_message(Message(response), topic_id=TopicId(user_topic_type, source=self.id.key))

@type_subscription(topic_type=user_topic_type)
class UserAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("A user agent that outputs the final copy to the user.")

    @message_handler
    async def handle_final_copy(self, message: Message, ctx: MessageContext) -> None:
        print(f"\n{'-'*80}\n{self.id.type} received final copy:\n{message.content}")

async def main():
    model_client = OpenAIChatCompletionClient(model="gpt-4o-mini")
    runtime = SingleThreadedAgentRuntime()
    await ConceptExtractorAgent.register(
        runtime, type=concept_extractor_topic_type, factory=lambda: ConceptExtractorAgent(model_client=model_client)
    )
    await WriterAgent.register(runtime, type=writer_topic_type, factory=lambda: WriterAgent(model_client=model_client))
    await FormatProofAgent.register(
        runtime, type=format_proof_topic_type, factory=lambda: FormatProofAgent(model_client=model_client)
    )
    await UserAgent.register(runtime, type=user_topic_type, factory=lambda: UserAgent())
    runtime.start()
    await runtime.publish_message(
        Message(content="An eco-friendly stainless steel water bottle that keeps drinks cold for 24 hours"),
        topic_id=TopicId(concept_extractor_topic_type, source="default"),
    )
    await runtime.stop_when_idle()
    await model_client.close()

if __name__ == "__main__":
    asyncio.run(main())
