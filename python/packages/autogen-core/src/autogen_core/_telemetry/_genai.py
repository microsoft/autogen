from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, Optional

from opentelemetry import trace
from opentelemetry.semconv._incubating.attributes.gen_ai_attributes import (
    GEN_AI_AGENT_DESCRIPTION,
    GEN_AI_AGENT_ID,
    GEN_AI_AGENT_NAME,
    GEN_AI_OPERATION_NAME,
    GEN_AI_SYSTEM,
    GEN_AI_TOOL_CALL_ID,
    GEN_AI_TOOL_DESCRIPTION,
    GEN_AI_TOOL_NAME,
    GenAiOperationNameValues,
)
from opentelemetry.trace import Span, SpanKind

# Constant for system name
GENAI_SYSTEM_AUTOGEN = "autogen"


@contextmanager
def trace_tool_span(
    tool_name: str,
    *,
    tracer: Optional[trace.Tracer] = None,
    parent: Optional[Span] = None,
    tool_description: Optional[str] = None,
    tool_call_id: Optional[str] = None,
    tool_arguments: Optional[str] = None,
) -> Generator[Span, Any, None]:
    """Context manager to create a span for tool execution following the
    OpenTelemetry Semantic conventions for generative AI systems.

    See the GenAI semantic conventions documentation:
    `OpenTelemetry GenAI Semantic Conventions <https://opentelemetry.io/docs/specs/semconv/gen-ai/>`__

    .. warning::

        The GenAI Semantic Conventions are still in incubation and
        subject to changes in future releases.


    Args:
        tool_name (str): The name of the tool being executed.
        tracer (Optional[trace.Tracer]): The tracer to use for creating the span.
        parent (Optional[Span]): The parent span to link this span to.
        tool_description (Optional[str]): A description of the tool.
        tool_call_id (Optional[str]): A unique identifier for the tool call.
        tool_arguments (Optional[str]): Arguments passed to the tool.
    """
    if tracer is None:
        tracer = trace.get_tracer("autogen-core")
    span_attributes = {
        GEN_AI_OPERATION_NAME: GenAiOperationNameValues.EXECUTE_TOOL.value,
        GEN_AI_SYSTEM: GENAI_SYSTEM_AUTOGEN,
        GEN_AI_TOOL_NAME: tool_name,
    }
    if tool_description is not None:
        span_attributes[GEN_AI_TOOL_DESCRIPTION] = tool_description
    if tool_call_id is not None:
        span_attributes[GEN_AI_TOOL_CALL_ID] = tool_call_id
    if tool_arguments is not None:
        span_attributes["autogen.tool.arguments"] = tool_arguments
    with tracer.start_as_current_span(
        f"{GenAiOperationNameValues.EXECUTE_TOOL.value} {tool_name}",
        kind=SpanKind.INTERNAL,
        context=trace.set_span_in_context(parent) if parent else None,
        attributes=span_attributes,
    ) as span:
        yield span


@contextmanager
def trace_create_agent_span(
    agent_name: str,
    *,
    tracer: Optional[trace.Tracer] = None,
    parent: Optional[Span] = None,
    agent_id: Optional[str] = None,
    agent_description: Optional[str] = None,
) -> Generator[Span, Any, None]:
    """Context manager to create a span for agent creation following the
    OpenTelemetry Semantic conventions for generative AI systems.

    See the GenAI semantic conventions documentation:
    `OpenTelemetry GenAI Semantic Conventions <https://opentelemetry.io/docs/specs/semconv/gen-ai/>`__

    .. warning::

        The GenAI Semantic Conventions are still in incubation and
        subject to changes in future releases.

    Args:
        agent_name (str): The name of the agent being created.
        tracer (Optional[trace.Tracer]): The tracer to use for creating the span.
        parent (Optional[Span]): The parent span to link this span to.
        agent_id (Optional[str]): The unique identifier for the agent.
        agent_description (Optional[str]): A description of the agent.
    """
    if tracer is None:
        tracer = trace.get_tracer("autogen-core")
    span_attributes = {
        GEN_AI_OPERATION_NAME: GenAiOperationNameValues.CREATE_AGENT.value,
        GEN_AI_SYSTEM: GENAI_SYSTEM_AUTOGEN,
        GEN_AI_AGENT_NAME: agent_name,
    }
    if agent_id is not None:
        span_attributes[GEN_AI_AGENT_ID] = agent_id
    if agent_description is not None:
        span_attributes[GEN_AI_AGENT_DESCRIPTION] = agent_description
    with tracer.start_as_current_span(
        f"{GenAiOperationNameValues.CREATE_AGENT.value} {agent_name}",
        kind=SpanKind.CLIENT,
        context=trace.set_span_in_context(parent) if parent else None,
        attributes=span_attributes,
    ) as span:
        yield span


@contextmanager
def trace_invoke_agent_span(
    agent_name: str,
    *,
    tracer: Optional[trace.Tracer] = None,
    parent: Optional[Span] = None,
    agent_id: Optional[str] = None,
    agent_description: Optional[str] = None,
) -> Generator[Span, Any, None]:
    """Context manager to create a span for invoking an agent following the
    OpenTelemetry Semantic conventions for generative AI systems.

    See the GenAI semantic conventions documentation:
    `OpenTelemetry GenAI Semantic Conventions <https://opentelemetry.io/docs/specs/semconv/gen-ai/>`__

    .. warning::

        The GenAI Semantic Conventions are still in incubation and
        subject to changes in future releases.

    Args:
        agent_name (str): The name of the agent being invoked.
        tracer (Optional[trace.Tracer]): The tracer to use for creating the span.
        parent (Optional[Span]): The parent span to link this span to.
        agent_id (Optional[str]): The unique identifier for the agent.
        agent_description (Optional[str]): A description of the agent.
    """
    if tracer is None:
        tracer = trace.get_tracer("autogen-core")
    span_attributes = {
        GEN_AI_OPERATION_NAME: GenAiOperationNameValues.INVOKE_AGENT.value,
        GEN_AI_SYSTEM: GENAI_SYSTEM_AUTOGEN,
        GEN_AI_AGENT_NAME: agent_name,
    }
    if agent_id is not None:
        span_attributes[GEN_AI_AGENT_ID] = agent_id
    if agent_description is not None:
        span_attributes[GEN_AI_AGENT_DESCRIPTION] = agent_description
    with tracer.start_as_current_span(
        f"{GenAiOperationNameValues.INVOKE_AGENT.value} {agent_name}",
        kind=SpanKind.CLIENT,
        context=trace.set_span_in_context(parent) if parent else None,
        attributes=span_attributes,
    ) as span:
        yield span
