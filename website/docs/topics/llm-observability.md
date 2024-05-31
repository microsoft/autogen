# LLM Observability

AutoGen supports advanced LLM observability and monitoring through built-in logging and partner providers.

## What is LLM Observability
AI agent observability is the ability to monitor, measure, and understand the internal states and behaviors of AI agent systems.
Observability is crucial for ensuring transparency, reliability, and accountability in your agent systems.


## Development

### Agent Development in Terminal is Limited
- Lose track of what your agents did in between executions
- Parsing through terminal output searching for LLM completions
- Printing “tool called”

### Agent Development Dashboards Enable More
- Visual dashboard so you can see what your agents did in human-readable format
- LLM calls are magically recorded - prompt, completion, timestamps for each - with one line of code
- Agents and their events (including tool calls) are recorded with one more line of code
- Errors are magically associated to its causal event
- Record any other events to your session with two more lines of code
- Tons of other useful data if you’re developing with supported agent frameworks: SDK version

## Compliance

Observability and monitoring is critical to ensure AI agent systems adhere to laws and regulations in industries like finance and healthcare, preventing violations such as data breaches and privacy issues.

- Insights into AI decision-making, allowing organizations to explain outcomes and build trust with stakeholders.
- Helps detect anomalies and unintended behaviors early, mitigating operational, financial, and reputational risks.
- Ensures compliance with data privacy regulations, preventing unauthorized access and misuse of sensitive information.
- Quick identification and response to compliance violations, supporting incident analysis and prevention.

## Available Observability Integrations

### Logging
- Autogen SQLite and File Logger - [Tutorial](/docs/notebooks/agentchat_logging)

### Full-Service Partners
Autogen is currently partnered with [AgentOps](https://agentops.ai) for seamless observability integration.

[Learn how to install AgentOps](/docs/notebooks/agentchat_agentops)
