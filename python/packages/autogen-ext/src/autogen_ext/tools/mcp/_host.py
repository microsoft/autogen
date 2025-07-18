import asyncio
import base64
import inspect
import io
import json
from typing import Any, Awaitable, Callable, Optional, Sequence

from autogen_core import AgentInstantiationContext, Image
from autogen_core._agent_id import AgentId
from autogen_core._agent_runtime import AgentRuntime
from autogen_core._cancellation_token import CancellationToken
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    FinishReasons,
    LLMMessage,
    SystemMessage,
    UserMessage,
)
from autogen_core.tools import BaseWorkbenchRequest, BaseWorkbenchResponse, WorkbenchHost
from autogen_core.tools._base import ErrorWorkbenchResponse
from PIL import Image as PILImage

from mcp import types as mcp_types
from mcp.types import StopReason

from ._base import (
    Elicitor,
    ElicitorTypes,
    ElicitWorkbenchRequest,
    ElicitWorkbenchResponse,
    InputFuncType,
    ListRootsWorkbenchRequest,
    ListRootsWorkbenchResult,
    SamplingWorkbenchRequest,
    SamplingWorkbenchResponse,
)


# TODO: check if using to_thread fixes this in jupyter
async def cancellable_input(prompt: str, cancellation_token: Optional[CancellationToken]) -> str:
    task: asyncio.Task[str] = asyncio.create_task(asyncio.to_thread(input, prompt))
    if cancellation_token is not None:
        cancellation_token.link_future(task)
    return await task


def _parse_sampling_content(
    content: mcp_types.TextContent | mcp_types.ImageContent | mcp_types.AudioContent,
) -> str | Image:
    """Convert MCP content types to Autogen content types."""
    if content.type == "text":
        return content.text
    elif content.type == "image":
        # Decode base64 image data and create PIL Image
        image_data = base64.b64decode(content.data)
        pil_image = PILImage.open(io.BytesIO(image_data))
        return Image.from_pil(pil_image)
    else:
        raise ValueError(f"Unsupported content type: {content.type}")


def _parse_sampling_message(message: mcp_types.SamplingMessage) -> LLMMessage:
    """Convert MCP sampling messages to Autogen messages."""
    content = _parse_sampling_content(message.content)
    if message.role == "user":
        return UserMessage(
            source="user",
            content=[content],
        )
    elif message.role == "assistant":
        assert isinstance(content, str), "Assistant messages only support string content."
        return AssistantMessage(
            source="assistant",
            content=content,
        )
    else:
        raise ValueError(f"Unrecognized message role: {message.role}")


def _finish_reason_to_stopReason(finish_reason: FinishReasons) -> StopReason:
    if finish_reason == "stop":
        return "endTurn"
    elif finish_reason == "length":
        return "maxTokens"
    else:
        return finish_reason


class InputFuncElicitor(Elicitor):
    """Handle MCP Elicit Requests by prompting the user on the command line"""

    def __init__(self, input_func: InputFuncType) -> None:
        self._input_func = input_func

    async def _get_input(self, prompt: str) -> str:
        if len(inspect.signature(self._input_func).parameters) == 2:
            # Function expects (prompt, cancellation_token)
            response = self._input_func(prompt, CancellationToken())  # type: ignore
        else:
            # Function expects only prompt
            response = self._input_func(prompt)  # type: ignore

        if inspect.isawaitable(response):
            response = await response

        return response

    async def elicit(self, request: mcp_types.ElicitRequest) -> mcp_types.ElicitResult:
        action = ""

        while action not in ("accept", "decline", "cancel"):
            action = await self._get_input(request.params.message + " (accept | decline | cancel)")
            action = action.lower()

        content = None
        while content is None:
            content = await self._get_input(json.dumps(request.params.requestedSchema, indent=2))
            try:
                content = json.loads(content)
            except Exception:
                content = None

        return mcp_types.ElicitResult(action=action, content=content)


class AgentElicitor(Elicitor):
    def __init__(self, runtime: AgentRuntime, recipient: AgentId) -> None:
        self._runtime = runtime
        self._recipient = recipient

    async def elicit(self, request: mcp_types.ElicitRequest) -> mcp_types.ElicitResult:
        response = await self._runtime.send_message(
            request.params.message,
            recipient=self._recipient,
        )
        return mcp_types.ElicitResult.model_validate(response)


class ElicitorFactory:
    @staticmethod
    def create(elicitor: ElicitorTypes):
        if isinstance(elicitor, Elicitor):
            return elicitor
        elif isinstance(elicitor, AgentId):
            runtime = AgentInstantiationContext.current_runtime()
            return AgentElicitor(runtime=runtime, recipient=elicitor)
        elif callable(elicitor):
            return InputFuncElicitor(input_func=elicitor)
        else:
            raise ValueError("Cannot create elicitor from arguments")


class McpWorkbenchHost(WorkbenchHost):
    """MCP workbench host that supports sampling, elicitation, and listing roots."""

    def __init__(
        self,
        model_client: ChatCompletionClient | None = None,
        roots: Sequence[mcp_types.Root] | Callable[[], Sequence[mcp_types.Root]] | None = None,
        elicitor: Elicitor | InputFuncType | AgentId | None = None,
    ):
        """Initialize the MCP workbench host.

        Args:
            model_client: Optional chat completion client for handling sampling requests.
            roots: Optional sequence of roots or callable returning roots.
            elicitor: Optional elicitor for handling elicitation requests.
            runtime: Optional runtime for sending messages to agents.
            sender_id: Optional sender ID for messages sent by this host.
        """
        self._model_client = model_client
        self._roots = roots
        self._elicitor = ElicitorFactory.create(elicitor) if elicitor else None

    def handle_workbench_request(self, request: BaseWorkbenchRequest) -> Awaitable[BaseWorkbenchResponse]:
        """Handle a request from a workbench by delegating to specific handler methods."""
        if isinstance(request, SamplingWorkbenchRequest):
            return self.handle_sampling_request(request)
        elif isinstance(request, ElicitWorkbenchRequest):
            return self.handle_elicit_request(request)
        elif isinstance(request, ListRootsWorkbenchRequest):
            return self.handle_list_roots_request(request)
        else:
            # Return error response for unsupported request types
            return self._create_error_response(request, f"Unsupported request type: {type(request).__name__}")

    async def handle_sampling_request(
        self, request: SamplingWorkbenchRequest
    ) -> SamplingWorkbenchResponse | ErrorWorkbenchResponse:
        """Handle a sampling request from the workbench.

        Args:
            request: The sampling request containing message creation parameters.

        Returns:
            A sampling response with the generated message.
        """
        if self._model_client is None:
            return await self._create_error_response(
                request,
                "No model client available for sampling requests",
            )

        try:
            # Convert MCP messages to AutoGen format using existing parser
            autogen_messages: list[LLMMessage] = []

            # Add system prompt if provided
            if request.systemPrompt:
                autogen_messages.append(SystemMessage(content=request.systemPrompt))

            # Parse sampling messages
            for msg in request.messages:
                autogen_messages.append(_parse_sampling_message(msg))

            # Use the model client to generate a response
            extra_args: dict[str, Any] = {"max_tokens": request.maxTokens}
            if request.temperature is not None:
                extra_args["temperature"] = request.temperature
            if request.stopSequences is not None:
                extra_args["stop"] = request.stopSequences

            response = await self._model_client.create(messages=autogen_messages, extra_create_args=extra_args)

            # Extract text content from response
            if isinstance(response.content, str):
                response_text = response.content
            else:
                import json

                # Handle function calls - convert to string representation
                response_text = json.dumps(response.content)

            return SamplingWorkbenchResponse(
                request_id=request.request_id,
                role="assistant",
                content=mcp_types.TextContent(type="text", text=response_text),
                model=self._model_client.model_info["family"],
                stopReason=_finish_reason_to_stopReason(response.finish_reason),
            )
        except Exception as e:
            return await self._create_error_response(
                request,
                f"Sampling request failed: {str(e)}",
            )

    async def handle_elicit_request(
        self, request: ElicitWorkbenchRequest
    ) -> ElicitWorkbenchResponse | ErrorWorkbenchResponse:
        """Handle an elicitation request from the workbench.

        Args:
            request: The elicitation request containing prompts and parameters.

        Returns:
            An elicitation response with the elicited information.
        """
        if self._elicitor is None:
            return await self._create_error_response(
                request,
                "No elicitor configured for this host",
            )

        try:
            response = await self._elicitor.elicit(request)
            return ElicitWorkbenchResponse.model_validate(response)
        except Exception as e:
            return await self._create_error_response(
                request,
                f"Elicitation request failed: {str(e)}",
            )

    async def handle_list_roots_request(
        self, request: ListRootsWorkbenchRequest
    ) -> ListRootsWorkbenchResult | ErrorWorkbenchResponse:
        """Handle a list roots request from the workbench.

        Args:
            request: The list roots request.

        Returns:
            A list roots response containing available roots.
        """
        if self._roots is None:
            return await self._create_error_response(request, "Host does not support listing roots")
        else:
            try:
                if callable(self._roots):
                    roots = self._roots()
                    if inspect.isawaitable(roots):
                        roots = await roots
                else:
                    roots = self._roots

                return ListRootsWorkbenchResult(request_id=request.request_id, roots=list(roots))
            except Exception as e:
                return await self._create_error_response(request, f"Caught error listing roots: {e}")

    async def _create_error_response(self, request: BaseWorkbenchRequest, error_message: str) -> ErrorWorkbenchResponse:
        """Create an error response for unsupported requests."""
        from autogen_core.tools import ErrorWorkbenchResponse

        return ErrorWorkbenchResponse(request_id=request.request_id, error=error_message)
