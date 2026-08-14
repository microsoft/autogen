# Agent and Multi-Agent Applications

An **agent** is a software entity that communicates via messages, maintains its own state, and performs actions in response to received messages or changes in its state. These actions may modify the agent’s state and produce external effects, such as updating message logs, sending new messages, executing code, or making API calls.

Many software systems can be modeled as a collection of independent agents that interact with one another. Examples include:

- Sensors on a factory floor
- Distributed services powering web applications
- Business workflows involving multiple stakeholders
- AI agents, such as those powered by language models (e.g., GPT-4), which can write code, interface with external systems, and communicate with other agents.

These systems, composed of multiple interacting agents, are referred to as **multi-agent applications**.

> **Note:**  
> AI agents typically use language models as part of their software stack to interpret messages, perform reasoning, and execute actions.

## Characteristics of Multi-Agent Applications

In multi-agent applications, agents may:

- Run within the same process or on the same machine
- Operate across different machines or organizational boundaries
- Be implemented in diverse programming languages and make use of different AI models or instructions
- Work together towards a shared goal, coordinating their actions through messaging

Each agent is a self-contained unit that can be developed, tested, and deployed independently. This modular design allows agents to be reused across different scenarios and composed into more complex systems.

Agents are inherently **composable**: simple agents can be combined to form complex, adaptable applications, where each agent contributes a specific function or service to the overall system.
