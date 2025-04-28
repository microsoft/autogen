from typing import List, cast
import chainlit as cl
import yaml
import uuid
import string
import asyncio
from dataclasses import dataclass

from autogen_core import (
    DefaultTopicId,
    FunctionCall,
    Image,
    MessageContext,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    TopicId,
    TypeSubscription,
    message_handler,
    CancellationToken,
    ClosureAgent,
    ClosureContext,
)
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    CreateResult,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_core.model_context import BufferedChatCompletionContext
from pydantic import BaseModel
from SimpleAssistantAgent import SimpleAssistantAgent, FinalResult

class GroupChatMessage(BaseModel):
    body: UserMessage

class RequestToSpeak(BaseModel):
    pass

assistant_topic_type = "assistant"
critic_topic_type = "critic"
group_chat_topic_type = "group_chat"

TASK_RESULTS_TOPIC_TYPE = "task-results"
task_results_topic_id = TopicId(type=TASK_RESULTS_TOPIC_TYPE, source="default")
CLOSURE_AGENT_TYPE = "collect_result_agent"

class BaseGroupChatAgent(RoutedAgent):

    def __init__(
        self,
        description: str,
        group_chat_topic_type: str,
        model_client: ChatCompletionClient,
        system_message: str,
    ) -> None:
        super().__init__(description=description)
        self._group_chat_topic_type = group_chat_topic_type
        self._model_client = model_client
        self._system_message = SystemMessage(content=system_message)
        self._chat_history: List[LLMMessage] = []

    @message_handler
    async def handle_message(self, message: GroupChatMessage, ctx: MessageContext) -> None:
        self._chat_history.extend(
            [
                UserMessage(content=f"Transferred to {message.body.source}", source="system"),
                message.body,
            ]
        )
    @message_handler
    async def handle_request_to_speak(self, message: RequestToSpeak, ctx: MessageContext) -> None:
        print(f"### {self.id.type}: ")
        self._chat_history.append(
            UserMessage(content=f"Transferred to {self.id.type}, adopt the persona immediately.", source="system")
        )
        # Run the chat completion with the tools.
        model_result: Optional[CreateResult] = None
        async for chunk in self._model_client.create_stream(
            messages=[self._system_message] + self._chat_history,
            cancellation_token=ctx.cancellation_token,
        ):
            if isinstance(chunk, CreateResult):
                model_result = chunk
                await self.runtime.publish_message(FinalResult("complete", self.id.type), topic_id=task_results_topic_id)
            elif isinstance(chunk, str):
                #yield ModelClientStreamingChunkEvent(content=chunk, source=agent_name)
                # foward the stream tokent to the Queue
                await self.runtime.publish_message(FinalResult("chunk", chunk), topic_id=task_results_topic_id)
            else:
                raise RuntimeError(f"Invalid chunk type: {type(chunk)}")

        if model_result is None:
            raise RuntimeError("No final model result in streaming mode.")
        self._chat_history.append(AssistantMessage(content=model_result.content, source=self.id.type))
        print(model_result.content, flush=True)
        await self.publish_message(
            GroupChatMessage(body=UserMessage(content=model_result.content, source=self.id.type)),
            topic_id=DefaultTopicId(type=self._group_chat_topic_type),
        )

class AssistantAgent(BaseGroupChatAgent):
    def __init__(self, description: str, group_chat_topic_type: str, model_client: ChatCompletionClient) -> None:
        super().__init__(
            description=description,
            group_chat_topic_type=group_chat_topic_type,
            model_client=model_client,
            system_message="You are a helpful assistant.",
        )


class CriticAgent(BaseGroupChatAgent):
    def __init__(self, description: str, group_chat_topic_type: str, model_client: ChatCompletionClient) -> None:
        super().__init__(
            description=description,
            group_chat_topic_type=group_chat_topic_type,
            model_client=model_client,
            system_message="You are a critic. Provide constructive feedback. "
            "Respond with 'APPROVE' if your feedback has been addressed.",
        )

class GroupChatManager(RoutedAgent):
    def __init__(
        self,
        participant_topic_types: List[str],
        model_client: ChatCompletionClient,
    ) -> None:
        super().__init__("Group chat manager")
        self._participant_topic_types = participant_topic_types
        self._model_client = model_client
        self._chat_history: List[UserMessage] = []
        self._previous_participant_idx = -1 

    @message_handler
    async def handle_message(self, message: GroupChatMessage, ctx: MessageContext) -> None:
        assert isinstance(message.body, UserMessage)
        self._chat_history.append(message.body)
        # If the message is an approval message from the user, stop the chat.
        if message.body.source == "User":
            assert isinstance(message.body.content, str)
            if message.body.content.lower().strip(string.punctuation).endswith("approve"):
                return
        print("Message source " + message.body.source + "My Message content " + message.body.content)
        if message.body.source == "critic":
            if ("approve" in message.body.content.lower().strip(string.punctuation)):
                print("Received approval from critic agent")
                await self.runtime.publish_message(FinalResult("stop", self.id.type), topic_id=task_results_topic_id)
                return
        # Simple round robin algorithm to call next client to speak
        selected_topic_type: str

        idx = self._previous_participant_idx +1
        if (idx == len(self._participant_topic_types)):
             idx = 0
        selected_topic_type = self._participant_topic_types[idx]
        self._previous_participant_idx = idx 

        await self.publish_message(RequestToSpeak(), DefaultTopicId(type=selected_topic_type))

        #raise ValueError(f"Invalid role selected: {completion.content}")

        #completion = await self._model_client.create([system_message], cancellation_token=ctx.cancellation_token)
        # assert isinstance(completion.content, str)

# Function called when closure agent receives message. It put the messages chunks to the output queue
# when the message is complete, it sends the message to Chainlit UI

async def output_result(_agent: ClosureContext, message: FinalResult, ctx: MessageContext) -> None:
    queue = cast(asyncio.Queue[FinalResult], cl.user_session.get("output_queue"))  # type: ignore
    await queue.put(message)
    if (message.type == "complete"):
        ui_resp = cl.Message(content= message.value + ": ")
        #print("In output result, reading the queue")
        while not queue.empty():
            result = await queue.get()
            if (result.type == "chunk"):
                #print("get chunk "+ result.value +" from queue")
                await ui_resp.stream_token(result.value)
            elif (result.type == "complete"):
                #print("get chunk "+ result.value +" from queue")
                await ui_resp.send()
                break

@cl.on_chat_start  # type: ignore
async def start_chat() -> None:

    # Load model configuration and create the model client.
    with open("model_config.yaml", "r") as f:
        model_config = yaml.safe_load(f)
    model_client = ChatCompletionClient.load_component(model_config)
    context = BufferedChatCompletionContext(buffer_size=10)

    runtime = SingleThreadedAgentRuntime()
    queue = asyncio.Queue[FinalResult]()

    # Create the assistant agent.
    assistant_agent_type = await AssistantAgent.register(runtime, "assistant", lambda: AssistantAgent(
        description="assistant",
        group_chat_topic_type=group_chat_topic_type,
        model_client=model_client,
        #system_message="You are a helpful assistant",
        #context=context,
        #model_client_stream=True,  # Enable model client streaming.
    ))

    # Assistant agent listen to assistant topic and group chat topic
    await runtime.add_subscription(TypeSubscription(topic_type=assistant_topic_type, agent_type=assistant_agent_type.type))
    await runtime.add_subscription(TypeSubscription(topic_type=group_chat_topic_type, agent_type=assistant_agent_type.type))

    # Create the critic agent.
    critic_agent_type = await CriticAgent.register(runtime, "critic", lambda: CriticAgent(
        description="critic", 
        group_chat_topic_type=group_chat_topic_type,
        model_client=model_client,
        #system_message="You are a critic. Provide constructive feedback. "
        #"Respond with 'APPROVE' if your feedback has been addressed.",
        #context=context,
        #model_client_stream=True,  # Enable model client streaming.
    ))

    # Critic agent listen to critic topic and group chat topic
    await runtime.add_subscription(TypeSubscription(topic_type=critic_topic_type, agent_type=critic_agent_type.type))
    await runtime.add_subscription(TypeSubscription(topic_type=group_chat_topic_type, agent_type=critic_agent_type.type))

    # Termination condition.
    #termination = TextMentionTermination("APPROVE", sources=["critic"])

    # Chain the assistant and critic agents using RoundRobinGroupChat.
    # group_chat = RoundRobinGroupChat([assistant, critic], termination_condition=termination)

    group_chat_manager_type = await GroupChatManager.register(
        runtime,
        "group_chat_manager",
        lambda: GroupChatManager(
            participant_topic_types=[assistant_topic_type, critic_topic_type],
            model_client=model_client,
        ),
    )
    await runtime.add_subscription(
        TypeSubscription(topic_type=group_chat_topic_type, agent_type=group_chat_manager_type.type)
    )

    # Register the Closure Agent, it will place streamed response into the output queue by calling output_result function
    await ClosureAgent.register_closure(
        runtime, CLOSURE_AGENT_TYPE, output_result, subscriptions=lambda:[TypeSubscription(topic_type=TASK_RESULTS_TOPIC_TYPE, agent_type=CLOSURE_AGENT_TYPE)]
    )
    runtime.start()  # Start processing messages in the background.

    # Save the runtime and output_queue in the chainlit user session.
    cl.user_session.set("prompt_history", "")  # type: ignore
    cl.user_session.set("run_time", runtime)  # type: ignore
    cl.user_session.set("output_queue", queue)  # type: ignore


@cl.set_starters  # type: ignore
async def set_starts() -> List[cl.Starter]:
    return [
        cl.Starter(
            label="Poem Writing",
            message="Write a poem about the ocean.",
        ),
        cl.Starter(
            label="Story Writing",
            message="Write a story about a detective solving a mystery.",
        ),
        cl.Starter(
            label="Write Code",
            message="Write a function that merge two list of numbers into single sorted list.",
        ),
    ]

@cl.on_message  # type: ignore
async def chat(message: cl.Message) -> None:
    # Construct the response message.
    response = cl.Message(content="")

    # Get the session data for process messages
    runtime = cast(SingleThreadedAgentRuntime, cl.user_session.get("run_time"))
    queue = cast(asyncio.Queue[FinalResult], cl.user_session.get("output_queue"))

    # Publish the user message to the Group Chat

    session_id = str(uuid.uuid4())
    await runtime.publish_message(
        GroupChatMessage(
            body=UserMessage(
                content=message.content,
                source="User",
            )
        ),
        TopicId(type=group_chat_topic_type, source=session_id),
    )