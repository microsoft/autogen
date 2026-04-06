# EU AI Act Compliance Guide for AutoGen Deployers

AutoGen is an open-source multi-agent orchestration framework. Under Article 25(4) of the EU AI Act, open-source tools released under a free license carry no compliance obligations themselves. AutoGen is Apache 2.0. It is exempt.

You are not. If you build a high-risk AI system using AutoGen and deploy it in the EU, the obligations land on you. This guide maps those obligations to AutoGen's architecture so you know exactly what to implement.

Enforcement begins **August 2, 2026**.

## 1. Scope: Is Your System High-Risk?

Before implementing anything, determine whether your AutoGen application falls under Annex III of the EU AI Act. Annex III lists eight categories of high-risk AI systems:

1. **Biometrics** (remote identification, emotion recognition)
2. **Critical infrastructure** (energy, transport, water, digital)
3. **Education** (admissions scoring, exam proctoring, learning assessment)
4. **Employment** (CV screening, interview evaluation, task allocation, performance monitoring)
5. **Essential services** (credit scoring, insurance risk, emergency dispatch)
6. **Law enforcement** (risk assessment, polygraph alternatives, evidence analysis)
7. **Migration and border control** (visa processing, risk indicators)
8. **Administration of justice** (sentencing assistance, case outcome prediction)

If your AutoGen system does not fall into these categories, your only obligation is Article 50 (user disclosure). Skip to Section 5.

If it does, keep reading.

## 2. Article 12: Record-Keeping

Article 12 requires automatic logging of events relevant to risk identification. Logs must be retained for at least six months. In AutoGen terms, capture:

- **Agent messages.** Every `TextMessage`, `MultiModalMessage`, `StopMessage`, and `HandoffMessage` between agents. This is the decision trail.
- **Tool calls.** Every `ToolCallRequestEvent` and `ToolCallExecutionEvent`, including external API calls and code execution results.
- **Model responses.** Raw LLM completions, token counts, and model identifiers.
- **Termination events.** Which `TerminationCondition` fired, and any exceptions raised.

AutoGen 0.4 supports OpenTelemetry tracing natively:

```python
from autogen_agentchat import TRACE_LOGGER_NAME
import logging

trace_logger = logging.getLogger(TRACE_LOGGER_NAME)
trace_logger.setLevel(logging.DEBUG)
trace_logger.addHandler(logging.FileHandler("autogen_traces.jsonl"))
```

For production, route traces to an OpenTelemetry backend (Jaeger, Grafana Tempo) with a retention policy meeting the six-month minimum.

## 3. Article 13: Transparency Documentation

Article 13 requires high-risk systems to be interpretable by deployers. You must document:

- **System architecture.** Agent roster, roles, backing models, interaction patterns. For `RoundRobinGroupChat`, document turn order. For `SocietyOfMindAgent`, document the inner team structure.
- **Decision boundaries.** Registered tools, permissions, and `TerminationCondition` configurations.
- **Intended purpose and limitations.** What the system does, what it should not be used for, known failure modes.
- **Human oversight.** How operators intervene or override. If using `HandoffMessage` for human-in-the-loop, document the escalation flow.

This goes to downstream deployers and, on request, to national competent authorities.

## 4. Article 25: Value Chain Accountability

Article 25 says every party contributing to a high-risk AI system bears obligations proportional to their role. This is where multi-agent systems get interesting.

A typical AutoGen deployment might chain: an `AssistantAgent` backed by GPT-4o making a recommendation, a second `AssistantAgent` backed by a different model validating it, a `SocietyOfMindAgent` resolving disagreements via an inner team, and tool calls to external services. Each link is a potential liability point.

**In practice:**

- **Model providers.** If you use LLM APIs from OpenAI, Anthropic, or others, verify their EU AI Act compliance documentation and terms of service.
- **Third-party tools.** External services your agents call (e.g., a credit scoring API) carry their own Article 25 obligations. Verify contractually.
- **Internal delegation.** Agent-to-agent delegation within your system does not split liability. A `SocietyOfMindAgent` wrapping a `RoundRobinGroupChat` is one system. You own the full chain.

## 5. Article 50: User Disclosure

If your AutoGen system interacts with humans, they must be informed it is AI. This applies to all AI systems, not just high-risk ones.

```python
from autogen_agentchat.agents import AssistantAgent

agent = AssistantAgent(
    name="support_agent",
    system_message=(
        "You are an AI assistant. Always inform the user "
        "they are communicating with an AI system, not a human."
    ),
)
```

A system message alone is insufficient. The disclosure must appear in your application's UI before or at the start of interaction, not just in the agent's prompt.

---

**Further reading:** [EU AI Act full text](https://artificialintelligenceact.eu/) | [Annex III high-risk categories](https://artificialintelligenceact.eu/annex/3/) | [AutoGen tracing documentation](https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tracing.html)
