from autogen_agentchat.agents import UserProxyAgent
from autogen_agentchat.agents._user_proxy_agent import UserProxyAgentConfig
from autogen_core import CancellationToken
from typing_extensions import Any, Mapping, Optional, Self


class A2aExternalUserProxyAgentConfig(UserProxyAgentConfig):
    """Configuration for A2aExternalUserProxyAgent.

    Attributes:
        is_cancelled_by_me (bool): Flag indicating if the agent initiated cancellation
    """

    is_cancelled_by_me: bool = False


class A2aExternalUserProxyAgent(UserProxyAgent):
    """External user proxy agent for A2A protocol integration.

    This agent acts as a bridge between the A2A protocol and external user interactions.
    It manages user input requests and cancellation handling in A2A workflows.

    Example:
        Basic usage:
        ```python
        agent = A2aExternalUserProxyAgent()
        response = await agent.request_input("Your choice?")
        ```

        Custom implementation with specific input handling:
        ```python
        class CustomUserProxy(A2aExternalUserProxyAgent):
            async def cancel_for_user_input(self, prompt: str, cancellation_token: CancellationToken) -> str:
                # Custom input handling logic
                if should_cancel():
                    self.is_cancelled_by_me = True
                    cancellation_token.cancel()
                    return "Cancelled due to specific condition"

                # Or delegate to external service
                result = await external_service.get_user_input(prompt)
                return result


        custom_agent = CustomUserProxy()
        ```

        Integration with web UI:
        ```python
        class WebUserProxy(A2aExternalUserProxyAgent):
            def __init__(self, web_socket):
                super().__init__()
                self.web_socket = web_socket

            async def cancel_for_user_input(self, prompt: str, cancellation_token: CancellationToken) -> str:
                # Send prompt to web UI
                await self.web_socket.send(prompt)

                # Wait for user response or cancellation
                try:
                    response = await self.web_socket.receive()
                    return response
                except TimeoutError:
                    self.is_cancelled_by_me = True
                    cancellation_token.cancel()
                    return "User input timed out"
        ```

    Note:
        - Override cancel_for_user_input for custom input handling
        - Maintain cancellation state with is_cancelled_by_me
        - Integrate with any external input source
        - Support async operations and timeouts
    """

    component_version = 1
    component_config_schema = A2aExternalUserProxyAgentConfig
    component_provider_override = "autogen_ext.runtimes.a2a.A2aExternalUserProxyAgent"

    def __init__(self) -> None:
        super().__init__(
            "ExternalUser",
            description="A proxy user agent to get input from external user.",
            input_func=self.cancel_for_user_input,
        )
        self.is_cancelled_by_me = False

    async def cancel_for_user_input(self, _prompt: str, cancellation_token: Optional[CancellationToken]) -> str:
        """Handle user input requests with cancellation support.

        This method is called when the agent needs user input. Override this method
        to implement custom input handling logic.

        Args:
            _prompt (str): The prompt to show to the user
            cancellation_token (CancellationToken): Token for managing cancellation

        Returns:
            str: The user's input or cancellation message

        Raises:
            AssertionError: If cancellation_token is not provided

        Example:
            REST API integration:
            ```python
            class RestApiUserProxy(A2aExternalUserProxyAgent):
                async def cancel_for_user_input(self, prompt: str, cancellation_token: CancellationToken) -> str:
                    try:
                        # Post prompt to API
                        async with aiohttp.ClientSession() as session:
                            async with session.post("/api/user/prompt", json={"prompt": prompt}) as resp:
                                if resp.status == 200:
                                    return await resp.text()

                        # Handle timeout or error
                        self.is_cancelled_by_me = True
                        cancellation_token.cancel()
                        return "API request failed"
                    except Exception as e:
                        self.is_cancelled_by_me = True
                        cancellation_token.cancel()
                        return f"Error: {str(e)}"
            ```

            CLI integration:
            ```python
            class CliUserProxy(A2aExternalUserProxyAgent):
                async def cancel_for_user_input(self, prompt: str, cancellation_token: CancellationToken) -> str:
                    try:
                        # Register Ctrl+C handler
                        def on_interrupt():
                            self.is_cancelled_by_me = True
                            cancellation_token.cancel()

                        # Show prompt and get input with timeout
                        print(prompt)
                        result = await asyncio.wait_for(asyncio.get_event_loop().run_in_executor(None, input), timeout=30.0)
                        return result
                    except asyncio.TimeoutError:
                        self.is_cancelled_by_me = True
                        cancellation_token.cancel()
                        return "Input timeout"
            ```

        Note:
            - Always check/set is_cancelled_by_me when cancelling
            - Use cancellation_token to signal cancellation
            - Handle timeouts and errors appropriately
            - Can integrate with any async input source
        """
        assert cancellation_token, "IllegalState Cancellation token must be provided."
        self.is_cancelled_by_me = True
        cancellation_token.cancel()
        return "User input cancelled by the a2a external agent."

    async def on_reset(self, cancellation_token: Optional[CancellationToken] = None) -> None:
        """Reset the agent to its initial state.

        This method resets the cancellation flag and underlying UserProxyAgent state.

        Args:
            cancellation_token (Optional[CancellationToken]): Optional token for cancellation

        Example:
            ```python
            # Reset agent state
            await agent.on_reset()

            # Reset with cancellation support
            token = CancellationToken()
            await agent.on_reset(token)
            ```

        Note:
            - Clears is_cancelled_by_me flag
            - Calls parent class reset
            - Prepares agent for new conversation
        """
        self.is_cancelled_by_me = False
        await super().on_reset(cancellation_token)

    @classmethod
    def _from_config(cls, config: Any) -> Self:
        return cls()

    async def save_state(self) -> Mapping[str, Any]:
        """Export the agent's current state.

        Returns:
            Mapping[str, Any]: Dictionary containing agent state

        Example:
            ```python
            # Save agent state
            state = await agent.save_state()

            # Persist state
            with open("agent_state.json", "w") as f:
                json.dump(state, f)
            ```

        Note:
            - Preserves cancellation state
            - Returns serializable state data
            - Used for agent persistence
        """
        return A2aExternalUserProxyAgentConfig(
            is_cancelled_by_me=self.is_cancelled_by_me, name="ExternalUser"
        ).model_dump()

    async def load_state(self, state: Mapping[str, Any]) -> None:
        """Restore the agent's state from saved data.

        Args:
            state (Mapping[str, Any]): Previously saved agent state

        Example:
            ```python
            # Load saved state
            with open("agent_state.json", "r") as f:
                state = json.load(f)

            # Restore agent
            await agent.load_state(state)
            ```

        Note:
            - Restores cancellation state
            - Validates state data
            - Can be extended for custom state
        """
        config = A2aExternalUserProxyAgentConfig.model_validate(state)
        self.is_cancelled_by_me = config.is_cancelled_by_me
