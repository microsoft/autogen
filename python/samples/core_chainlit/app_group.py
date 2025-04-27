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
user_topic_type = "User"
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
"""
    @message_handler
    async def handle_request_to_speak(self, message: RequestToSpeak, ctx: MessageContext) -> None:
        print(f"### {self.id.type}: ")
        self._chat_history.append(
            UserMessage(content=f"Transferred to {self.id.type}, adopt the persona immediately.", source="system")
        )
        completion = await self._model_client.create([self._system_message] + self._chat_history)
        assert isinstance(completion.content, str)
        self._chat_history.append(AssistantMessage(content=completion.content, source=self.id.type))
        print(completion.content, flush=True)
        await self.publish_message(
            GroupChatMessage(body=UserMessage(content=completion.content, source=self.id.type)),
            topic_id=DefaultTopicId(type=self._group_chat_topic_type),
        )
"""
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

# Function called when closure agent receives message. It put the messages to the output queue
async def output_result(_agent: ClosureContext, message: FinalResult, ctx: MessageContext) -> None:
    queue = cast(asyncio.Queue[FinalResult], cl.user_session.get("output_queue"))  # type: ignore
    print( "Adding " + message.value + "to queue")
    await queue.put(message)

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
    """
    assistant_agent_type = await SimpleAssistantAgent.register(runtime, "assistant", lambda: SimpleAssistantAgent(
        name="assistant",
        model_client=model_client,
        #system_message="You are a helpful assistant",
        #context=context,
        #model_client_stream=True,  # Enable model client streaming.
    ))
    """

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
    """
    critic_agent_type = await SimpleAssistantAgent.register(runtime, "critic", lambda: SimpleAssistantAgent(
        name="critic",
        model_client=model_client,
        system_message="You are a critic. Provide constructive feedback. "
        "Respond with 'APPROVE' if your feedback has been addressed.",
        #context=context,
        #model_client_stream=True,  # Enable model client streaming.
    ))
    """
    await runtime.add_subscription(TypeSubscription(topic_type=critic_topic_type, agent_type=critic_agent_type.type))
    await runtime.add_subscription(TypeSubscription(topic_type=group_chat_topic_type, agent_type=critic_agent_type.type))

    # Termination condition.
    # termination = TextMentionTermination("APPROVE", sources=["critic"])

    # Chain the assistant and critic agents using RoundRobinGroupChat.
    # group_chat = RoundRobinGroupChat([assistant, critic], termination_condition=termination)

    group_chat_manager_type = await GroupChatManager.register(
        runtime,
        "group_chat_manager",
        lambda: GroupChatManager(
            participant_topic_types=[assistant_topic_type, critic_topic_type, user_topic_type],
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
    # Set the assistant agent in the user session.
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

"""
@cl.on_message  # type: ignore
async def chat(message: cl.Message) -> None:
    # Get the team from the user session.
    team = cast(RoundRobinGroupChat, cl.user_session.get("team"))  # type: ignore
    # Streaming response message.
    streaming_response: cl.Message | None = None
    # Stream the messages from the team.
    async for msg in team.run_stream(
        task=[TextMessage(content=message.content, source="user")],
        cancellation_token=CancellationToken(),
    ):
        if isinstance(msg, ModelClientStreamingChunkEvent):
            # Stream the model client response to the user.
            if streaming_response is None:
                # Start a new streaming response.
                streaming_response = cl.Message(content=msg.source + ": ", author=msg.source)
            await streaming_response.stream_token(msg.content)
        elif streaming_response is not None:
            # Done streaming the model client response.
            # We can skip the current message as it is just the complete message
            # of the streaming response.
            await streaming_response.send()
            # Reset the streaming response so we won't enter this block again
            # until the next streaming response is complete.
            streaming_response = None
        elif isinstance(msg, TaskResult):
            # Send the task termination message.
            final_message = "Task terminated. "
            if msg.stop_reason:
                final_message += msg.stop_reason
            await cl.Message(content=final_message).send()
        else:
            # Skip all other message types.
            pass
"""
@cl.on_message  # type: ignore
async def chat(message: cl.Message) -> None:
    # Construct the response message.
    response = cl.Message(content="")

    # Get the session data for process messages
    runtime = cast(SingleThreadedAgentRuntime, cl.user_session.get("run_time"))
    queue = cast(asyncio.Queue[FinalResult], cl.user_session.get("output_queue"))

    # Send message to the Assistant Agent
    # response = await runtime.send_message(UserMessage(content=message.content, source="User"), AgentId("assistant_agent", "default"))
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
    #await runtime.stop_when_idle()
    # Forward the reponses inside the output queue to the chainlit UI
    # task1 = asyncio.create_task(runtime.send_message(message, AgentId("simple_agent", "default")))

    # Consume items from the response queue until the stream ends or an error occurs
    """
    while TRUE:
        item = await queue.get().value
        if item is STREAM_DONE:
            print(f"{time.time():.2f} - MAIN: Received STREAM_DONE. Exiting loop.")
            break
        elif isinstance(item, str) and item.startswith("ERROR:"):
            print(f"{time.time():.2f} - MAIN: Received error message from agent: {item}")
            break
        else:
            yield json.dumps({'content': item}) + '\n'
    await task1       
    """
    ui_resp = cl.Message(content="")
    print("Reading the queue")
    while not queue.empty():
        #print((result := await queue.get()).value)
        result = await queue.get().value
        print("Queue is not Empty")
        if (result.type == "chunk"):
            await ui_resp.stream_token(result.value)
        elif (result.type == "response"):
            await ui_resp.send()
            break
    print("Queue is empty") 
