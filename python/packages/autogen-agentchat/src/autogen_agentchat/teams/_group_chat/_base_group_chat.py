import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Callable, Dict, List, Mapping, Sequence

from autogen_core import (
    AgentId,
    AgentRuntime,
    AgentType,
    CancellationToken,
    ComponentBase,
    SingleThreadedAgentRuntime,
    TypeSubscription,
)
from pydantic import BaseModel, ValidationError

from ... import EVENT_LOGGER_NAME
from ...base import ChatAgent, TaskResult, Team, TerminationCondition
from ...messages import (
    AgentEvent,
    ChatMessage,
    MessageFactory,
    ModelClientStreamingChunkEvent,
    StopMessage,
    TextMessage,
)
from ...state import TeamState
from ._chat_agent_container import ChatAgentContainer
from ._events import GroupChatPause, GroupChatReset, GroupChatResume, GroupChatStart, GroupChatTermination
from ._sequential_routed_agent import SequentialRoutedAgent

event_logger = logging.getLogger(EVENT_LOGGER_NAME)


class BaseGroupChat(Team, ABC, ComponentBase[BaseModel]):
    """The base class for group chat teams.

    To implement a group chat team, first create a subclass of :class:`BaseGroupChatManager` and then
    create a subclass of :class:`BaseGroupChat` that uses the group chat manager.
    """

    component_type = "team"

    def __init__(
        self,
        participants: List[ChatAgent],
        group_chat_manager_name: str,
        group_chat_manager_class: type[SequentialRoutedAgent],
        termination_condition: TerminationCondition | None = None,
        max_turns: int | None = None,
        runtime: AgentRuntime | None = None,
        custom_message_types: List[type[AgentEvent | ChatMessage]] | None = None,
    ):
        if len(participants) == 0:
            raise ValueError("At least one participant is required.")
        if len(participants) != len(set(participant.name for participant in participants)):
            raise ValueError("The participant names must be unique.")
        self._participants = participants
        self._base_group_chat_manager_class = group_chat_manager_class
        self._termination_condition = termination_condition
        self._max_turns = max_turns
        self._message_factory = MessageFactory()
        if custom_message_types is not None:
            for message_type in custom_message_types:
                self._message_factory.register(message_type)

        # The team ID is a UUID that is used to identify the team and its participants
        # in the agent runtime. It is used to create unique topic types for each participant.
        # Currently, team ID is binded to an object instance of the group chat class.
        # So if you create two instances of group chat, there will be two teams with different IDs.
        self._team_id = str(uuid.uuid4())

        # Constants for the group chat team.
        # The names are used to identify the agents within the team.
        # The names may not be unique across different teams.
        self._group_chat_manager_name = group_chat_manager_name
        self._participant_names: List[str] = [participant.name for participant in participants]
        self._participant_descriptions: List[str] = [participant.description for participant in participants]
        # The group chat topic type is used for broadcast communication among all participants and the group chat manager.
        self._group_topic_type = f"group_topic_{self._team_id}"
        # The group chat manager topic type is used for direct communication with the group chat manager.
        self._group_chat_manager_topic_type = f"{self._group_chat_manager_name}_{self._team_id}"
        # The participant topic types are used for direct communication with each participant.
        self._participant_topic_types: List[str] = [
            f"{participant.name}_{self._team_id}" for participant in participants
        ]
        # The output topic type is used for emitting streaming messages from the group chat.
        # The group chat manager will relay the messages to the output message queue.
        self._output_topic_type = f"output_topic_{self._team_id}"

        # The queue for collecting the output messages.
        self._output_message_queue: asyncio.Queue[AgentEvent | ChatMessage | GroupChatTermination] = asyncio.Queue()

        # Create a runtime for the team.
        if runtime is not None:
            self._runtime = runtime
            self._embedded_runtime = False
        else:
            # Use a embedded single-threaded runtime for the group chat.
            # Background exceptions must not be ignored as it results in non-surfaced exceptions and early team termination.
            self._runtime = SingleThreadedAgentRuntime(ignore_unhandled_exceptions=False)
            self._embedded_runtime = True

        # Flag to track if the group chat has been initialized.
        self._initialized = False

        # Flag to track if the group chat is running.
        self._is_running = False

    @abstractmethod
    def _create_group_chat_manager_factory(
        self,
        name: str,
        group_topic_type: str,
        output_topic_type: str,
        participant_topic_types: List[str],
        participant_names: List[str],
        participant_descriptions: List[str],
        output_message_queue: asyncio.Queue[AgentEvent | ChatMessage | GroupChatTermination],
        termination_condition: TerminationCondition | None,
        max_turns: int | None,
        message_factory: MessageFactory,
    ) -> Callable[[], SequentialRoutedAgent]: ...

    def _create_participant_factory(
        self,
        parent_topic_type: str,
        output_topic_type: str,
        agent: ChatAgent,
        message_factory: MessageFactory,
    ) -> Callable[[], ChatAgentContainer]:
        def _factory() -> ChatAgentContainer:
            container = ChatAgentContainer(parent_topic_type, output_topic_type, agent, message_factory)
            return container

        return _factory

    async def _init(self, runtime: AgentRuntime) -> None:
        # Constants for the group chat manager.
        group_chat_manager_agent_type = AgentType(self._group_chat_manager_topic_type)

        # Register participants.
        # Use the participant topic type as the agent type.
        for participant, agent_type in zip(self._participants, self._participant_topic_types, strict=True):
            # Register the participant factory.
            await ChatAgentContainer.register(
                runtime,
                type=agent_type,
                factory=self._create_participant_factory(
                    self._group_topic_type, self._output_topic_type, participant, self._message_factory
                ),
            )
            # Add subscriptions for the participant.
            # The participant should be able to receive messages from its own topic.
            await runtime.add_subscription(TypeSubscription(topic_type=agent_type, agent_type=agent_type))
            # The participant should be able to receive messages from the group topic.
            await runtime.add_subscription(TypeSubscription(topic_type=self._group_topic_type, agent_type=agent_type))

        # Register the group chat manager.
        await self._base_group_chat_manager_class.register(
            runtime,
            type=group_chat_manager_agent_type.type,
            factory=self._create_group_chat_manager_factory(
                name=self._group_chat_manager_name,
                group_topic_type=self._group_topic_type,
                output_topic_type=self._output_topic_type,
                participant_names=self._participant_names,
                participant_topic_types=self._participant_topic_types,
                participant_descriptions=self._participant_descriptions,
                output_message_queue=self._output_message_queue,
                termination_condition=self._termination_condition,
                max_turns=self._max_turns,
                message_factory=self._message_factory,
            ),
        )
        # Add subscriptions for the group chat manager.
        # The group chat manager should be able to receive messages from the its own topic.
        await runtime.add_subscription(
            TypeSubscription(
                topic_type=self._group_chat_manager_topic_type, agent_type=group_chat_manager_agent_type.type
            )
        )
        # The group chat manager should be able to receive messages from the group topic.
        await runtime.add_subscription(
            TypeSubscription(topic_type=self._group_topic_type, agent_type=group_chat_manager_agent_type.type)
        )
        # The group chat manager will relay the messages from output topic to the output message queue.
        await runtime.add_subscription(
            TypeSubscription(topic_type=self._output_topic_type, agent_type=group_chat_manager_agent_type.type)
        )

        self._initialized = True

    async def run(
        self,
        *,
        task: str | ChatMessage | Sequence[ChatMessage] | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> TaskResult:
        """Run the team and return the result. The base implementation uses
        :meth:`run_stream` to run the team and then returns the final result.
        Once the team is stopped, the termination condition is reset.

        Args:
            task (str | ChatMessage | Sequence[ChatMessage] | None): The task to run the team with. Can be a string, a single :class:`ChatMessage` , or a list of :class:`ChatMessage`.
            cancellation_token (CancellationToken | None): The cancellation token to kill the task immediately.
                Setting the cancellation token potentially put the team in an inconsistent state,
                and it may not reset the termination condition.
                To gracefully stop the team, use :class:`~autogen_agentchat.conditions.ExternalTermination` instead.

        Returns:
            result: The result of the task as :class:`~autogen_agentchat.base.TaskResult`. The result contains the messages produced by the team and the stop reason.

        Example using the :class:`~autogen_agentchat.teams.RoundRobinGroupChat` team:


        .. code-block:: python

            import asyncio
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.conditions import MaxMessageTermination
            from autogen_agentchat.teams import RoundRobinGroupChat
            from autogen_ext.models.openai import OpenAIChatCompletionClient


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(model="gpt-4o")

                agent1 = AssistantAgent("Assistant1", model_client=model_client)
                agent2 = AssistantAgent("Assistant2", model_client=model_client)
                termination = MaxMessageTermination(3)
                team = RoundRobinGroupChat([agent1, agent2], termination_condition=termination)

                result = await team.run(task="Count from 1 to 10, respond one at a time.")
                print(result)

                # Run the team again without a task to continue the previous task.
                result = await team.run()
                print(result)


            asyncio.run(main())


        Example using the :class:`~autogen_core.CancellationToken` to cancel the task:

        .. code-block:: python

            import asyncio
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.conditions import MaxMessageTermination
            from autogen_agentchat.teams import RoundRobinGroupChat
            from autogen_core import CancellationToken
            from autogen_ext.models.openai import OpenAIChatCompletionClient


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(model="gpt-4o")

                agent1 = AssistantAgent("Assistant1", model_client=model_client)
                agent2 = AssistantAgent("Assistant2", model_client=model_client)
                termination = MaxMessageTermination(3)
                team = RoundRobinGroupChat([agent1, agent2], termination_condition=termination)

                cancellation_token = CancellationToken()

                # Create a task to run the team in the background.
                run_task = asyncio.create_task(
                    team.run(
                        task="Count from 1 to 10, respond one at a time.",
                        cancellation_token=cancellation_token,
                    )
                )

                # Wait for 1 second and then cancel the task.
                await asyncio.sleep(1)
                cancellation_token.cancel()

                # This will raise a cancellation error.
                await run_task


            asyncio.run(main())
        """
        result: TaskResult | None = None
        async for message in self.run_stream(
            task=task,
            cancellation_token=cancellation_token,
        ):
            if isinstance(message, TaskResult):
                result = message
        if result is not None:
            return result
        raise AssertionError("The stream should have returned the final result.")

    async def run_stream(
        self,
        *,
        task: str | ChatMessage | Sequence[ChatMessage] | None = None,
        cancellation_token: CancellationToken | None = None,
    ) -> AsyncGenerator[AgentEvent | ChatMessage | TaskResult, None]:
        """Run the team and produces a stream of messages and the final result
        of the type :class:`~autogen_agentchat.base.TaskResult` as the last item in the stream. Once the
        team is stopped, the termination condition is reset.

        .. note::

            If an agent produces :class:`~autogen_agentchat.messages.ModelClientStreamingChunkEvent`,
            the message will be yielded in the stream but it will not be included in the
            :attr:`~autogen_agentchat.base.TaskResult.messages`.

        Args:
            task (str | ChatMessage | Sequence[ChatMessage] | None): The task to run the team with. Can be a string, a single :class:`ChatMessage` , or a list of :class:`ChatMessage`.
            cancellation_token (CancellationToken | None): The cancellation token to kill the task immediately.
                Setting the cancellation token potentially put the team in an inconsistent state,
                and it may not reset the termination condition.
                To gracefully stop the team, use :class:`~autogen_agentchat.conditions.ExternalTermination` instead.

        Returns:
            stream: an :class:`~collections.abc.AsyncGenerator` that yields :class:`~autogen_agentchat.messages.AgentEvent`, :class:`~autogen_agentchat.messages.ChatMessage`, and the final result :class:`~autogen_agentchat.base.TaskResult` as the last item in the stream.

        Example using the :class:`~autogen_agentchat.teams.RoundRobinGroupChat` team:

        .. code-block:: python

            import asyncio
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.conditions import MaxMessageTermination
            from autogen_agentchat.teams import RoundRobinGroupChat
            from autogen_ext.models.openai import OpenAIChatCompletionClient


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(model="gpt-4o")

                agent1 = AssistantAgent("Assistant1", model_client=model_client)
                agent2 = AssistantAgent("Assistant2", model_client=model_client)
                termination = MaxMessageTermination(3)
                team = RoundRobinGroupChat([agent1, agent2], termination_condition=termination)

                stream = team.run_stream(task="Count from 1 to 10, respond one at a time.")
                async for message in stream:
                    print(message)

                # Run the team again without a task to continue the previous task.
                stream = team.run_stream()
                async for message in stream:
                    print(message)


            asyncio.run(main())


        Example using the :class:`~autogen_core.CancellationToken` to cancel the task:

        .. code-block:: python

            import asyncio
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.conditions import MaxMessageTermination
            from autogen_agentchat.ui import Console
            from autogen_agentchat.teams import RoundRobinGroupChat
            from autogen_core import CancellationToken
            from autogen_ext.models.openai import OpenAIChatCompletionClient


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(model="gpt-4o")

                agent1 = AssistantAgent("Assistant1", model_client=model_client)
                agent2 = AssistantAgent("Assistant2", model_client=model_client)
                termination = MaxMessageTermination(3)
                team = RoundRobinGroupChat([agent1, agent2], termination_condition=termination)

                cancellation_token = CancellationToken()

                # Create a task to run the team in the background.
                run_task = asyncio.create_task(
                    Console(
                        team.run_stream(
                            task="Count from 1 to 10, respond one at a time.",
                            cancellation_token=cancellation_token,
                        )
                    )
                )

                # Wait for 1 second and then cancel the task.
                await asyncio.sleep(1)
                cancellation_token.cancel()

                # This will raise a cancellation error.
                await run_task


            asyncio.run(main())

        """

        # Create the messages list if the task is a string or a chat message.
        messages: List[ChatMessage] | None = None
        if task is None:
            pass
        elif isinstance(task, str):
            messages = [TextMessage(content=task, source="user")]
        elif isinstance(task, ChatMessage):
            messages = [task]
        elif isinstance(task, list):
            if not task:
                raise ValueError("Task list cannot be empty.")
            messages = []
            for msg in task:
                if not isinstance(msg, ChatMessage):
                    raise ValueError("All messages in task list must be valid ChatMessage types")
                messages.append(msg)
        else:
            raise ValueError("Task must be a string, a ChatMessage, or a list of ChatMessage.")
        # Check if the messages types are registered with the message factory.
        if messages is not None:
            for msg in messages:
                if not self._message_factory.is_registered(msg.__class__):
                    raise ValueError(
                        f"Message type {msg.__class__} is not registered with the message factory. "
                        "Please register it with the message factory by adding it to the "
                        "custom_message_types list when creating the team."
                    )

        if self._is_running:
            raise ValueError("The team is already running, it cannot run again until it is stopped.")
        self._is_running = True

        if self._embedded_runtime:
            # Start the embedded runtime.
            assert isinstance(self._runtime, SingleThreadedAgentRuntime)
            self._runtime.start()

        if not self._initialized:
            await self._init(self._runtime)

        shutdown_task: asyncio.Task[None] | None = None
        if self._embedded_runtime:

            async def stop_runtime() -> None:
                assert isinstance(self._runtime, SingleThreadedAgentRuntime)
                try:
                    # This will propagate any exceptions raised.
                    await self._runtime.stop_when_idle()
                finally:
                    # Stop the consumption of messages and end the stream.
                    # NOTE: we also need to put a GroupChatTermination event here because when the group chat
                    # has an exception, the group chat manager may not be able to put a GroupChatTermination event in the queue.
                    await self._output_message_queue.put(
                        GroupChatTermination(
                            message=StopMessage(content="Exception occurred.", source=self._group_chat_manager_name)
                        )
                    )

            # Create a background task to stop the runtime when the group chat
            # is stopped or has an exception.
            shutdown_task = asyncio.create_task(stop_runtime())

        try:
            # Run the team by sending the start message to the group chat manager.
            # The group chat manager will start the group chat by relaying the message to the participants
            # and the group chat manager.
            await self._runtime.send_message(
                GroupChatStart(messages=messages),
                recipient=AgentId(type=self._group_chat_manager_topic_type, key=self._team_id),
                cancellation_token=cancellation_token,
            )
            # Collect the output messages in order.
            output_messages: List[AgentEvent | ChatMessage] = []
            stop_reason: str | None = None
            # Yield the messsages until the queue is empty.
            while True:
                message_future = asyncio.ensure_future(self._output_message_queue.get())
                if cancellation_token is not None:
                    cancellation_token.link_future(message_future)
                # Wait for the next message, this will raise an exception if the task is cancelled.
                message = await message_future
                if isinstance(message, GroupChatTermination):
                    # If the message is None, it means the group chat has terminated.
                    # TODO: how do we handle termination when the runtime is not embedded
                    # and there is an exception in the group chat?
                    # The group chat manager may not be able to put a GroupChatTermination event in the queue,
                    # and this loop will never end.
                    stop_reason = message.message.content
                    break
                yield message
                if isinstance(message, ModelClientStreamingChunkEvent):
                    # Skip the model client streaming chunk events.
                    continue
                output_messages.append(message)

            # Yield the final result.
            yield TaskResult(messages=output_messages, stop_reason=stop_reason)

        finally:
            try:
                if shutdown_task is not None:
                    # Wait for the shutdown task to finish.
                    # This will propagate any exceptions raised.
                    await shutdown_task
            finally:
                # Clear the output message queue.
                while not self._output_message_queue.empty():
                    self._output_message_queue.get_nowait()

                # Indicate that the team is no longer running.
                self._is_running = False

    async def reset(self) -> None:
        """Reset the team and its participants to their initial state.

        The team must be stopped before it can be reset.

        Raises:
            RuntimeError: If the team has not been initialized or is currently running.

        Example using the :class:`~autogen_agentchat.teams.RoundRobinGroupChat` team:

        .. code-block:: python

            import asyncio
            from autogen_agentchat.agents import AssistantAgent
            from autogen_agentchat.conditions import MaxMessageTermination
            from autogen_agentchat.teams import RoundRobinGroupChat
            from autogen_ext.models.openai import OpenAIChatCompletionClient


            async def main() -> None:
                model_client = OpenAIChatCompletionClient(model="gpt-4o")

                agent1 = AssistantAgent("Assistant1", model_client=model_client)
                agent2 = AssistantAgent("Assistant2", model_client=model_client)
                termination = MaxMessageTermination(3)
                team = RoundRobinGroupChat([agent1, agent2], termination_condition=termination)
                stream = team.run_stream(task="Count from 1 to 10, respond one at a time.")
                async for message in stream:
                    print(message)

                # Reset the team.
                await team.reset()
                stream = team.run_stream(task="Count from 1 to 10, respond one at a time.")
                async for message in stream:
                    print(message)


            asyncio.run(main())
        """

        if not self._initialized:
            await self._init(self._runtime)

        if self._is_running:
            raise RuntimeError("The group chat is currently running. It must be stopped before it can be reset.")
        self._is_running = True

        if self._embedded_runtime:
            # Start the runtime.
            assert isinstance(self._runtime, SingleThreadedAgentRuntime)
            self._runtime.start()

        try:
            # Send a reset messages to all participants.
            for participant_topic_type in self._participant_topic_types:
                await self._runtime.send_message(
                    GroupChatReset(),
                    recipient=AgentId(type=participant_topic_type, key=self._team_id),
                )
            # Send a reset message to the group chat manager.
            await self._runtime.send_message(
                GroupChatReset(),
                recipient=AgentId(type=self._group_chat_manager_topic_type, key=self._team_id),
            )
        finally:
            if self._embedded_runtime:
                # Stop the runtime.
                assert isinstance(self._runtime, SingleThreadedAgentRuntime)
                await self._runtime.stop_when_idle()

            # Reset the output message queue.
            while not self._output_message_queue.empty():
                self._output_message_queue.get_nowait()

            # Indicate that the team is no longer running.
            self._is_running = False

    async def pause(self) -> None:
        """Pause its participants when the team is running by calling their
        :meth:`~autogen_agentchat.base.ChatAgent.on_pause` method via direct RPC calls.

        .. attention::

            This is an experimental feature introduced in v0.4.9 and may subject
            to change or removal in the future.

        The team must be initialized before it can be paused.

        Different from termination, pausing the team does not cause the
        :meth:`run` or :meth:`run_stream` method to return. It calls the
        :meth:`~autogen_agentchat.base.ChatAgent.on_pause` method on each
        participant, and if the participant does not implement the method, it
        will be a no-op.

        .. note::

            It is the responsibility of the agent class to handle the pause
            and ensure that the agent can be resumed later.
            Make sure to implement the :meth:`~autogen_agentchat.agents.BaseChatAgent.on_pause`
            method in your agent class for custom pause behavior.
            By default, the agent will not do anything when called.

        Raises:
            RuntimeError: If the team has not been initialized. Exceptions from
                the participants when calling their implementations of
                :class:`~autogen_agentchat.base.ChatAgent.on_pause` are
                propagated to this method and raised.
        """
        if not self._initialized:
            raise RuntimeError("The group chat has not been initialized. It must be run before it can be paused.")

        # Send a pause message to all participants.
        for participant_topic_type in self._participant_topic_types:
            await self._runtime.send_message(
                GroupChatPause(),
                recipient=AgentId(type=participant_topic_type, key=self._team_id),
            )
        # Send a pause message to the group chat manager.
        await self._runtime.send_message(
            GroupChatPause(),
            recipient=AgentId(type=self._group_chat_manager_topic_type, key=self._team_id),
        )

    async def resume(self) -> None:
        """Resume its participants when the team is running and paused by calling their
        :meth:`~autogen_agentchat.base.ChatAgent.on_resume` method via direct RPC calls.

        .. attention::

            This is an experimental feature introduced in v0.4.9 and may subject
            to change or removal in the future.

        The team must be initialized before it can be resumed.

        Different from termination and restart with a new task, resuming the team
        does not cause the :meth:`run` or :meth:`run_stream` method to return.
        It calls the :meth:`~autogen_agentchat.base.ChatAgent.on_resume` method on each
        participant, and if the participant does not implement the method, it
        will be a no-op.

        .. note::

            It is the responsibility of the agent class to handle the resume
            and ensure that the agent continues from where it was paused.
            Make sure to implement the :meth:`~autogen_agentchat.agents.BaseChatAgent.on_resume`
            method in your agent class for custom resume behavior.

        Raises:
            RuntimeError: If the team has not been initialized. Exceptions from
                the participants when calling their implementations of :class:`~autogen_agentchat.base.ChatAgent.on_resume`
                method are propagated to this method and raised.

        """
        if not self._initialized:
            raise RuntimeError("The group chat has not been initialized. It must be run before it can be resumed.")

        # Send a resume message to all participants.
        for participant_topic_type in self._participant_topic_types:
            await self._runtime.send_message(
                GroupChatResume(),
                recipient=AgentId(type=participant_topic_type, key=self._team_id),
            )
        # Send a resume message to the group chat manager.
        await self._runtime.send_message(
            GroupChatResume(),
            recipient=AgentId(type=self._group_chat_manager_topic_type, key=self._team_id),
        )

    async def save_state(self) -> Mapping[str, Any]:
        """Save the state of the group chat team.

        The state is saved by calling the :meth:`~autogen_core.AgentRuntime.agent_save_state` method
        on each participant and the group chat manager with their internal agent ID.
        The state is returned as a nested dictionary: a dictionary with key `agent_states`,
        which is a dictionary the agent names as keys and the state as values.

        .. code-block:: text

            {
                "agent_states": {
                    "agent1": ...,
                    "agent2": ...,
                    "RoundRobinGroupChatManager": ...
                }
            }

        .. note::

            Starting v0.4.9, the state is using the agent name as the key instead of the agent ID,
            and the `team_id` field is removed from the state. This is to allow the state to be
            portable across different teams and runtimes. States saved with the old format
            may not be compatible with the new format in the future.

        .. caution::

            When calling :func:`~autogen_agentchat.teams.BaseGroupChat.save_state` on a team
            while it is running, the state may not be consistent and may result in an unexpected state.
            It is recommended to call this method when the team is not running or after it is stopped.

        """
        if not self._initialized:
            await self._init(self._runtime)

        # Store state of each agent by their name.
        # NOTE: we don't use the agent ID as the key here because we need to be able to decouple
        # the state of the agents from their identities in the agent runtime.
        agent_states: Dict[str, Mapping[str, Any]] = {}
        # Save the state of all participants.
        for name, agent_type in zip(self._participant_names, self._participant_topic_types, strict=True):
            agent_id = AgentId(type=agent_type, key=self._team_id)
            # NOTE: We are using the runtime's save state method rather than the agent instance's
            # save_state method because we want to support saving state of remote agents.
            agent_states[name] = await self._runtime.agent_save_state(agent_id)
        # Save the state of the group chat manager.
        agent_id = AgentId(type=self._group_chat_manager_topic_type, key=self._team_id)
        agent_states[self._group_chat_manager_name] = await self._runtime.agent_save_state(agent_id)
        return TeamState(agent_states=agent_states).model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Load an external state and overwrite the current state of the group chat team.

        The state is loaded by calling the :meth:`~autogen_core.AgentRuntime.agent_load_state` method
        on each participant and the group chat manager with their internal agent ID.
        See :meth:`~autogen_agentchat.teams.BaseGroupChat.save_state` for the expected format of the state.
        """
        if not self._initialized:
            await self._init(self._runtime)

        if self._is_running:
            raise RuntimeError("The team cannot be loaded while it is running.")
        self._is_running = True

        try:
            team_state = TeamState.model_validate(state)
            # Load the state of all participants.
            for name, agent_type in zip(self._participant_names, self._participant_topic_types, strict=True):
                agent_id = AgentId(type=agent_type, key=self._team_id)
                if name not in team_state.agent_states:
                    raise ValueError(f"Agent state for {name} not found in the saved state.")
                await self._runtime.agent_load_state(agent_id, team_state.agent_states[name])
            # Load the state of the group chat manager.
            agent_id = AgentId(type=self._group_chat_manager_topic_type, key=self._team_id)
            if self._group_chat_manager_name not in team_state.agent_states:
                raise ValueError(f"Agent state for {self._group_chat_manager_name} not found in the saved state.")
            await self._runtime.agent_load_state(agent_id, team_state.agent_states[self._group_chat_manager_name])

        except ValidationError as e:
            raise ValueError(
                "Invalid state format. The expected state format has changed since v0.4.9. "
                "Please read the release note on GitHub."
            ) from e

        finally:
            # Indicate that the team is no longer running.
            self._is_running = False
