from typing import List, cast
import chainlit as cl
import yaml
import uuid
import string
import asyncio

from autogen_core import (
    ClosureAgent,
    ClosureContext,
    DefaultTopicId,
    MessageContext,
    message_handler,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    TopicId,
    TypeSubscription,
)
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    CreateResult,
    #LLMMessage,
    UserMessage,
)

from SimpleAssistantAgent import SimpleAssistantAgent, StreamResult, GroupChatMessage, RequestToSpeak

assistant_topic_type = "assistant"
critic_topic_type = "critic"
group_chat_topic_type = "group_chat"

TASK_RESULTS_TOPIC_TYPE = "task-results"
task_results_topic_id = TopicId(type=TASK_RESULTS_TOPIC_TYPE, source="default")
CLOSURE_AGENT_TYPE = "collect_result_agent"

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
            if message.body.content.lower().strip(string.punctuation).endswith("approve"): # type: ignore
                await self.runtime.publish_message(StreamResult(content="stop", source=self.id.type), topic_id=task_results_topic_id)
                return
        if message.body.source == "Critic":
            #if ("approve" in message.body.content.lower().strip(string.punctuation)):
            if message.body.content.lower().strip(string.punctuation).endswith("approve"): # type: ignore
                stop_msg = AssistantMessage(content="Task Finished", source=self.id.type)
                await self.runtime.publish_message(StreamResult(content=stop_msg, source=self.id.type), topic_id=task_results_topic_id)
                return

        # Simple round robin algorithm to call next client to speak
        selected_topic_type: str
        idx = self._previous_participant_idx +1
        if (idx == len(self._participant_topic_types)):
             idx = 0
        selected_topic_type = self._participant_topic_types[idx]
        self._previous_participant_idx = idx 

        # Send the RequestToSpeak message to next agent
        await self.publish_message(RequestToSpeak(), DefaultTopicId(type=selected_topic_type))

# Function called when closure agent receives message. It put the messages to the output queue
async def output_result(_agent: ClosureContext, message: StreamResult, ctx: MessageContext) -> None:
    queue = cast(asyncio.Queue[StreamResult], cl.user_session.get("queue_stream"))  # type: ignore
    await queue.put(message)

@cl.on_chat_start  # type: ignore
async def start_chat() -> None:

    # Load model configuration and create the model client.
    with open("model_config.yaml", "r") as f:
        model_config = yaml.safe_load(f)
    model_client = ChatCompletionClient.load_component(model_config)

    runtime = SingleThreadedAgentRuntime()
    cl.user_session.set("run_time", runtime)    # type: ignore
    queue = asyncio.Queue[StreamResult]()
    cl.user_session.set("queue_stream", queue)  # type: ignore

    # Create the assistant agent.
    assistant_agent_type = await SimpleAssistantAgent.register(runtime, "Assistant", lambda: SimpleAssistantAgent(
        name="Assistant",
        group_chat_topic_type=group_chat_topic_type,
        model_client=model_client,
        system_message="You are a helpful assistant",
        model_client_stream=True,  # Enable model client streaming.
    ))

    # Assistant agent listen to assistant topic and group chat topic
    await runtime.add_subscription(TypeSubscription(topic_type=assistant_topic_type, agent_type=assistant_agent_type.type))
    await runtime.add_subscription(TypeSubscription(topic_type=group_chat_topic_type, agent_type=assistant_agent_type.type))

    # Create the critic agent.
    critic_agent_type = await SimpleAssistantAgent.register(runtime, "Critic", lambda: SimpleAssistantAgent(
        name="Critic", 
        group_chat_topic_type=group_chat_topic_type,
        model_client=model_client,
        system_message="You are a critic. Provide constructive feedback.  Respond with 'APPROVE' if your feedback has been addressed.",
        model_client_stream=True,  # Enable model client streaming.
    ))

    # Critic agent listen to critic topic and group chat topic
    await runtime.add_subscription(TypeSubscription(topic_type=critic_topic_type, agent_type=critic_agent_type.type))
    await runtime.add_subscription(TypeSubscription(topic_type=group_chat_topic_type, agent_type=critic_agent_type.type))

    # Chain the assistant and critic agents using group_chat_manager.
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

    cl.user_session.set("prompt_history", "")  # type: ignore


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

async def pass_msg_to_ui() -> None:
    queue = cast(asyncio.Queue[StreamResult], cl.user_session.get("queue_stream"))  # type: ignore
    ui_resp = cl.Message("") 
    first_message = True
    while True:
        stream_msg = await queue.get()
        if (isinstance(stream_msg.content, str)):
            if (first_message):
                ui_resp = cl.Message(content= stream_msg.source + ": ")
                first_message = False
            await ui_resp.stream_token(stream_msg.content)
        elif (isinstance(stream_msg.content, CreateResult)):
            await ui_resp.send()
            ui_resp = cl.Message("") 
            first_message = True
        else:
            # This is a stop meesage
            if (stream_msg.content.content == "stop"):
                break
            break


@cl.on_message  # type: ignore
async def chat(message: cl.Message) -> None:
    # Construct the response message.

    # Get the runtime and queue from the session 
    runtime = cast(SingleThreadedAgentRuntime, cl.user_session.get("run_time"))  # type: ignore
    queue = cast(asyncio.Queue[StreamResult], cl.user_session.get("queue_stream"))  # type: ignore
    output_msg = cl.Message(content="")
    cl.user_session.set("output_msg", output_msg) # type: ignore

    # Publish the user message to the Group Chat
    session_id = str(uuid.uuid4())
    await runtime.publish_message( GroupChatMessage( body=UserMessage(
                content=message.content,
                source="User",
            )
        ),
        TopicId(type=group_chat_topic_type, source=session_id),)
    task1 = asyncio.create_task( pass_msg_to_ui())
    await task1