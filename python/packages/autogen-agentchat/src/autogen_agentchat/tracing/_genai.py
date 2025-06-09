from contextlib import contextmanager
from typing import Optional

from opentelemetry import trace
from opentelemetry.trace import SpanKind, Span
from opentelemetry.semconv._incubating.attributes.gen_ai_attributes import (
    GEN_AI_OPERATION_NAME,
    GEN_AI_SYSTEM,
    GEN_AI_AGENT_NAME,
    GEN_AI_AGENT_ID,
    GEN_AI_AGENT_DESCRIPTION,
    GenAiOperationNameValues,
)

# Constant for system name
GENAI_SYSTEM_AUTOGEN = "autogen"


@contextmanager
def trace_create_agent_span(
    agent_name: str,
    *,
    parent: Optional[Span] = None,
    agent_id: Optional[str] = None,
    agent_description: Optional[str] = None,
):
    tracer = trace.get_tracer("autogen-agentchat")
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
    parent: Optional[Span] = None,
    agent_id: Optional[str] = None,
    agent_description: Optional[str] = None,
):
    tracer = trace.get_tracer("autogen-agentchat")
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
