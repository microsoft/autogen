# Application Stack

AutoGen core is designed to be an unopinionated framework that can be used to build
a wide variety of multi-agent applications. It is not tied to any specific
agent abstraction or multi-agent pattern.

The following diagram shows the application stack.

![Application Stack](application-stack.svg)

At the bottom of the stack is the base messaging and routing facilities that
enable agents to communicate with each other. These are managed by the
agent runtime, and for most applications, developers only need to interact
with the high-level APIs provided by the runtime (see [Agent and Agent Runtime](../framework/agent-and-agent-runtime.ipynb)).

At the top of the stack, developers need to define the
types of the messages that agents exchange. This set of message types
forms a behavior contract that agents must adhere to, and the
implementation of the contracts determines how agents handle messages.
The behavior contract is also sometimes referred to as the message protocol.
It is the developer's responsibility to implement the behavior contract.
Multi-agent patterns emerge from these behavior contracts
(see [Multi-Agent Design Patterns](../design-patterns/multi-agent-design-patterns.md)).

## An Example Application

Consider a concrete example of a multi-agent application for
code generation. The application consists of three agents:
Coder Agent, Executor Agent, and Reviewer Agent.
The following diagram shows the data flow between the agents,
and the message types exchanged between them.

![Code Generation Example](code-gen-example.svg)

In this example, the behavior contract consists of the following:

- `CodingTaskMsg` message from application to the Coder Agent
- `CodeGenMsg` from Coder Agent to Executor Agent
- `ExecutionResultMsg` from Executor Agent to Reviewer Agent
- `ReviewMsg` from Reviewer Agent to Coder Agent
- `CodingResultMsg` from the Reviewer Agent to the application

The behavior contract is implemented by the agents' handling of these messages. For example, the Reviewer Agent listens for `ExecutionResultMsg`
and evaluates the code execution result to decide whether to approve or reject,
if approved, it sends a `CodingResultMsg` to the application,
otherwise, it sends a `ReviewMsg` to the Coder Agent for another round of
code generation.

This behavior contract is a case of a multi-agent pattern called _reflection_,
where a generation result is reviewed by another round of generation,
to improve the overall quality.
