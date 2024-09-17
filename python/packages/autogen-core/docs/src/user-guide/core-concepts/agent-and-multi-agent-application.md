# Agent and Multi-Agent Application

An agent is a software entity that
communicates via messages, maintains a state,
and performs actions in response to messages or a change in its state.
Actions can result in changes to the agent's state and external effects,
for example, updating message history, sending a message, executing code,
or making external API calls.

A wide variety of software applications can be modeled as a collection of independent
agents that communicate with each other:
sensors on a factory floor,
distributed services powering web applications,
business workflows involving multiple stakeholders,
and more recently, artificial intelligence (AI) agents powered by language models
(e.g., GPT-4) that can write code and interact with
other software systems.
We refer to them as multi-agent applications.

```{note}
AI agents make use of language models as part of
their software stacks to perform actions. 
```

In a multi-agent application, agents can live in the same process, on the same machine,
or on different machines and across organizational boundaries.
They can be implemented using different AI models, instructions, and programming languages.
They can collaborate and work toward a common goal.

Each agent is a self-contained unit:
developers can build, test and deploy it independently, and reuse it for different scenarios.
Agents are composable: simple agents can form complex applications.
