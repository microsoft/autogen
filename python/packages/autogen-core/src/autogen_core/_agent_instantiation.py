from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, ClassVar, Generator

from ._agent_id import AgentId
from ._agent_runtime import AgentRuntime


class AgentInstantiationContext:
    """A static class that provides context for agent instantiation.

    This static class can be used to access the current runtime and agent ID
    during agent instantiation -- inside the factory function or the agent's
    class constructor.

    Example:

        Get the current runtime and agent ID inside the factory function and
        the agent's constructor:

        .. code-block:: python

            import asyncio
            from dataclasses import dataclass

            from autogen_core import (
                AgentId,
                AgentInstantiationContext,
                MessageContext,
                RoutedAgent,
                SingleThreadedAgentRuntime,
                message_handler,
            )


            @dataclass
            class TestMessage:
                content: str


            class TestAgent(RoutedAgent):
                def __init__(self, description: str):
                    super().__init__(description)
                    # Get the current runtime -- we don't use it here, but it's available.
                    _ = AgentInstantiationContext.current_runtime()
                    # Get the current agent ID.
                    agent_id = AgentInstantiationContext.current_agent_id()
                    print(f"Current AgentID from constructor: {agent_id}")

                @message_handler
                async def handle_test_message(self, message: TestMessage, ctx: MessageContext) -> None:
                    print(f"Received message: {message.content}")


            def test_agent_factory() -> TestAgent:
                # Get the current runtime -- we don't use it here, but it's available.
                _ = AgentInstantiationContext.current_runtime()
                # Get the current agent ID.
                agent_id = AgentInstantiationContext.current_agent_id()
                print(f"Current AgentID from factory: {agent_id}")
                return TestAgent(description="Test agent")


            async def main() -> None:
                # Create a SingleThreadedAgentRuntime instance.
                runtime = SingleThreadedAgentRuntime()

                # Start the runtime.
                runtime.start()

                # Register the agent type with a factory function.
                await runtime.register_factory("test_agent", test_agent_factory)

                # Send a message to the agent. The runtime will instantiate the agent and call the message handler.
                await runtime.send_message(TestMessage(content="Hello, world!"), AgentId("test_agent", "default"))

                # Stop the runtime.
                await runtime.stop()


            asyncio.run(main())

    """

    def __init__(self) -> None:
        raise RuntimeError(
            "AgentInstantiationContext cannot be instantiated. It is a static class that provides context management for agent instantiation."
        )

    _AGENT_INSTANTIATION_CONTEXT_VAR: ClassVar[ContextVar[tuple[AgentRuntime, AgentId]]] = ContextVar(
        "_AGENT_INSTANTIATION_CONTEXT_VAR"
    )

    @classmethod
    @contextmanager
    def populate_context(cls, ctx: tuple[AgentRuntime, AgentId]) -> Generator[None, Any, None]:
        """:meta private:"""
        token = AgentInstantiationContext._AGENT_INSTANTIATION_CONTEXT_VAR.set(ctx)
        try:
            yield
        finally:
            AgentInstantiationContext._AGENT_INSTANTIATION_CONTEXT_VAR.reset(token)

    @classmethod
    def current_runtime(cls) -> AgentRuntime:
        try:
            return cls._AGENT_INSTANTIATION_CONTEXT_VAR.get()[0]
        except LookupError as e:
            raise RuntimeError(
                "AgentInstantiationContext.runtime() must be called within an instantiation context such as when the AgentRuntime is instantiating an agent. Mostly likely this was caused by directly instantiating an agent instead of using the AgentRuntime to do so."
            ) from e

    @classmethod
    def current_agent_id(cls) -> AgentId:
        try:
            return cls._AGENT_INSTANTIATION_CONTEXT_VAR.get()[1]
        except LookupError as e:
            raise RuntimeError(
                "AgentInstantiationContext.agent_id() must be called within an instantiation context such as when the AgentRuntime is instantiating an agent. Mostly likely this was caused by directly instantiating an agent instead of using the AgentRuntime to do so."
            ) from e

    @classmethod
    def is_in_factory_call(cls) -> bool:
        if cls._AGENT_INSTANTIATION_CONTEXT_VAR.get(None) is None:
            return False
        return True
