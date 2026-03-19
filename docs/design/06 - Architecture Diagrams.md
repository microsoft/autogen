# Architecture Diagrams

Visual reference for AutoGen's internal architecture. These diagrams complement the written design documents and should be kept in sync as the system evolves.

## Agent Runtime Architecture

AutoGen supports two runtime modes. Both expose the same programming interface to agents — the only difference is how messages are routed.

### Standalone Runtime

All agents live in a single process. The runtime manages message dispatch and agent lifecycle directly.

```mermaid
graph TB
    App["Application Code"]

    subgraph Runtime["SingleThreadedAgentRuntime"]
        Router["Message Router"]
        Subs["Subscription Table"]
        Catalog["Agent Catalog"]

        Router -->|"lookup"| Subs
        Router -->|"activate / dispatch"| Catalog
    end

    subgraph Agents["Agent Instances"]
        A1["Agent A<br/>(type: coder)"]
        A2["Agent B<br/>(type: reviewer)"]
        A3["Agent C<br/>(type: executor)"]
    end

    App -->|"publish / send_message"| Router
    Catalog --> A1
    Catalog --> A2
    Catalog --> A3
    A1 -->|"publish"| Router
    A2 -->|"publish"| Router
    A3 -->|"publish"| Router
```

### Distributed Runtime

Agents run across multiple worker processes. A central host servicer coordinates routing, while workers advertise the agent types they support and manage local agent lifecycles.

```mermaid
graph TB
    subgraph Host["Host Servicer"]
        GW["Gateway"]
        Directory["Agent Directory"]
        GW <-->|"resolve"| Directory
    end

    subgraph Worker1["Worker Process 1"]
        GW1["Gateway Client"]
        WCat1["Local Catalog"]
        AgA["Agent A"]
        AgB["Agent B"]
        GW1 --> WCat1
        WCat1 --> AgA
        WCat1 --> AgB
    end

    subgraph Worker2["Worker Process 2"]
        GW2["Gateway Client"]
        WCat2["Local Catalog"]
        AgC["Agent C"]
        AgD["Agent D"]
        GW2 --> WCat2
        WCat2 --> AgC
        WCat2 --> AgD
    end

    GW1 <-->|"gRPC"| GW
    GW2 <-->|"gRPC"| GW
```

## Agent Type Hierarchy

AutoGen layers two abstraction levels: a low-level core agent model and a higher-level AgentChat API built on top of it.

```mermaid
classDiagram
    class Agent {
        <<interface>>
        +id: AgentId
        +metadata: dict
        +on_message(message, ctx)
    }

    class RoutedAgent {
        +message_handler()
        +publish_message()
        +send_message()
    }

    class BaseChatAgent {
        <<abstract>>
        +name: str
        +description: str
        +on_messages(messages, token)
        +on_reset(token)
    }

    class AssistantAgent {
        +model_client
        +tools
        +system_message
    }

    class CodeExecutorAgent {
        +code_executor
    }

    class UserProxyAgent {
        +input_func
    }

    class SocietyOfMindAgent {
        +inner_team: Team
    }

    class MessageFilterAgent {
        +inner_agent
        +filter
    }

    class BaseGroupChat {
        <<abstract>>
        +participants: List
        +run(task)
        +run_stream(task)
    }

    class RoundRobinGroupChat
    class SelectorGroupChat
    class Swarm
    class MagenticOneGroupChat
    class GraphFlow

    Agent <|-- RoutedAgent
    RoutedAgent <|.. BaseChatAgent : wraps
    BaseChatAgent <|-- AssistantAgent
    BaseChatAgent <|-- CodeExecutorAgent
    BaseChatAgent <|-- UserProxyAgent
    BaseChatAgent <|-- SocietyOfMindAgent
    BaseChatAgent <|-- MessageFilterAgent
    BaseGroupChat <|-- RoundRobinGroupChat
    BaseGroupChat <|-- SelectorGroupChat
    BaseGroupChat <|-- Swarm
    BaseGroupChat <|-- MagenticOneGroupChat
    BaseGroupChat <|-- GraphFlow
```

## Message Flow: Publish-Subscribe

The core communication primitive is publish-subscribe. Agents subscribe to topic types, and the runtime matches published messages to subscribers.

```mermaid
sequenceDiagram
    participant App as Application
    participant RT as Runtime
    participant Sub as Subscription Table
    participant A as Coder Agent
    participant B as Executor Agent
    participant C as Reviewer Agent

    App->>RT: publish(CodingTaskMsg, topic="task")
    RT->>Sub: match topic "task"
    Sub-->>RT: [Coder Agent]
    RT->>A: deliver CodingTaskMsg

    A->>RT: publish(CodeGenMsg, topic="execution")
    RT->>Sub: match topic "execution"
    Sub-->>RT: [Executor Agent]
    RT->>B: deliver CodeGenMsg

    B->>RT: publish(ExecutionResultMsg, topic="review")
    RT->>Sub: match topic "review"
    Sub-->>RT: [Reviewer Agent]
    RT->>C: deliver ExecutionResultMsg

    alt Approved
        C->>RT: publish(CodingResultMsg, topic="output")
        RT->>App: deliver CodingResultMsg
    else Needs Revision
        C->>RT: publish(ReviewMsg, topic="task")
        RT->>Sub: match topic "task"
        Sub-->>RT: [Coder Agent]
        RT->>A: deliver ReviewMsg
        Note over A,C: Cycle repeats until approved
    end
```

## AgentChat Team Execution

When using the high-level AgentChat API, a Team orchestrates multi-agent conversations. Each team type uses a different strategy to select the next speaker.

```mermaid
sequenceDiagram
    participant User as Application
    participant Team as Team (e.g., SelectorGroupChat)
    participant Mgr as GroupChatManager
    participant A as Agent 1
    participant B as Agent 2
    participant C as Agent 3

    User->>Team: run(task="Build a web app")
    Team->>Mgr: start orchestration

    loop Until termination condition
        Mgr->>Mgr: select next speaker
        Mgr->>A: on_messages(context)
        A-->>Mgr: Response
        Mgr->>Mgr: append to shared context

        Mgr->>Mgr: select next speaker
        Mgr->>B: on_messages(context)
        B-->>Mgr: Response
        Mgr->>Mgr: check termination

        Mgr->>Mgr: select next speaker
        Mgr->>C: on_messages(context)
        C-->>Mgr: HandoffMessage or Response
        Mgr->>Mgr: check termination
    end

    Mgr-->>Team: TaskResult
    Team-->>User: TaskResult
```

## Team Pattern Comparison

A quick reference for how the built-in team types differ in their speaker-selection strategy.

```mermaid
graph LR
    subgraph RoundRobin["Round Robin"]
        direction LR
        RR_A["Agent A"] --> RR_B["Agent B"] --> RR_C["Agent C"] --> RR_A
    end

    subgraph Selector["Selector Group Chat"]
        direction TB
        S_LLM["LLM Selector"]
        S_A["Agent A"]
        S_B["Agent B"]
        S_C["Agent C"]
        S_LLM -->|"picks"| S_A
        S_LLM -->|"picks"| S_B
        S_LLM -->|"picks"| S_C
    end

    subgraph SwarmPattern["Swarm"]
        direction TB
        SW_A["Agent A"]
        SW_B["Agent B"]
        SW_C["Agent C"]
        SW_A -->|"handoff()"| SW_B
        SW_B -->|"handoff()"| SW_C
        SW_C -->|"handoff()"| SW_A
    end

    subgraph Graph["GraphFlow"]
        direction TB
        G_A["Agent A"]
        G_B["Agent B"]
        G_C["Agent C"]
        G_A --> G_B
        G_A --> G_C
        G_B --> G_C
    end
```

## Worker Protocol Lifecycle

The protocol between a worker process and the host servicer in a distributed deployment follows three phases.

```mermaid
stateDiagram-v2
    [*] --> Connecting: Worker starts
    Connecting --> Registering: Connection established

    state Registering {
        [*] --> RegisterAgentType
        RegisterAgentType --> RegisterAgentType: more types
        RegisterAgentType --> [*]: done
    }

    Registering --> Operating: Registration complete

    state Operating {
        [*] --> Idle
        Idle --> ProcessingEvent: Event received
        Idle --> ProcessingRPC: RpcRequest received
        ProcessingEvent --> Idle: handled
        ProcessingRPC --> SendResponse: generate RpcResponse
        SendResponse --> Idle: response sent
    }

    Operating --> Disconnecting: shutdown signal
    Disconnecting --> [*]: cleanup complete
```
