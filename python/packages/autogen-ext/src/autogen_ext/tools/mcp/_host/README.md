# MCP Session Host

The `McpSessionHost` supports MCP Server -> MCP Host requests within the AutoGen ecosystem. By design it should require minimal or no changes to your AutoGen agents, simply provide a host to the `McpWorkbench`.

The following MCP features are supported:

1. **Sampling**: Text generation using language models
2. **Elicitation**: Interactive user prompting and structured data collection
3. **Roots**: File system root listing for server access

## Architecture

```mermaid
flowchart LR
  %% Source Agent layer
  subgraph Source_Agent ["Source Agent"]
    direction TB
    WB[MCP Workbench]
    HS[MCP Session Host]
    R["Roots (static or callable)"]
    
    %% Abstract Elicitor
    E{Elicitor Type}

    %% Concrete Elicitors
    subgraph Elicitor_Subclasses ["Concrete Elicitors"]
        GCAE[GroupChatAgentElicitor]
        CCCE[ChatCompletionClientElicitor]
    end
  end


  %% Server layer: tool execution
  subgraph MCP_Server ["MCP Server"]
    MS[MCP Server]
  end

  %% Agent runtime layer (distributed)
  subgraph Agent_Runtime ["Agent Runtime"]
    GC[GroupChat]
  end

  %% Target Agent layer (can be distributed)
  subgraph Target_Agent ["Target Agent"]
    TA{Target Agent}
    %% Concrete Target Agents
    subgraph Target_Agent_Subclasses ["Concrete Target Agents"]
        UPA[UserProxyAgent]
        AA[AssistantAgent]
    end
  end

  %% Chat Completion Client
  CCC[Chat Completion Client]

  %% Flows
  WB -->|tool call| MS
  MS -.->|sampling/elicitation/roots| WB

  WB -->|sampling/elicitation/roots| HS

  HS -->|roots| R

  %% Elicitation via abstract Elicitor
  HS -->|elicitation| E
  E --> GCAE
  E --> CCCE

  %% GroupChat branch
  GCAE -->|elicitation| GC
  GC  -->|elicitation| TA
  TA  --> UPA
  TA  --> AA

  UPA -->|input| U["User"]
  AA -->|completion| CCC


  %% CCC branch
  CCCE -->|completion| CCC

  %% Sampling stays direct to CCC
  HS -->|sampling| CCC
```

## Sequence Diagrams

### Normal Tool Calling Flow

```mermaid
sequenceDiagram
    participant Assistant as AutoGen Assistant
    participant Workbench as McpWorkbench
    participant Server as MCP Server
    participant ModelClient as ChatCompletionClient

    Assistant->>Workbench: call_tool(tool, args)
    Workbench->>Server: execute tool
    Note over Server: Tool execution does not require host resources
    Server->>Workbench: tool result
    Workbench->>Assistant: tool execution result
```


### Sampling Request Flow

```mermaid
sequenceDiagram
    participant Assistant as AutoGen Assistant
    participant Workbench as McpWorkbench
    participant Server as MCP Server
    participant Host as McpSessionHost
    participant ModelClient as ChatCompletionClient

    Assistant->>Workbench: call_tool(tool, args)
    Workbench->>Server: execute tool
    Note over Server: Tool execution requires text generation
    Server->>Workbench: sampling request
    Workbench->>Host: handle_sampling_request()
    Host->>Host: convert MCP messages to AutoGen format
    Host->>ModelClient: create(messages, extra_args)
    ModelClient->>Host: response with content
    Host->>Host: convert response to MCP format
    Host->>Workbench: CreateMessageResult
    Workbench->>Server: sampling response
    Server->>Workbench: tool result
    Workbench->>Assistant: tool execution result
```

### Elicitation Request Flow

```mermaid
sequenceDiagram
    sequenceDiagram
    participant Assistant as AutoGen Assistant
    participant Workbench as McpWorkbench
    participant Server as MCP Server
    participant Host as McpSessionHost
    participant Elicitor as GroupChatAgentElicitor
    participant Runtime as AgentRuntime
    participant TargetAgent as Target Agent
    participant ModelClient as ChatCompletionClient
    participant User

    Assistant->>Workbench: call_tool(tool, args)
    Workbench->>Server: execute tool
    Note over Server: Tool needs user input with structured response
    Server->>Workbench: ElicitRequest
    Workbench->>Host: handle_elicit_request()
    Host->>Elicitor: elicit(params)
    Elicitor->>Runtime: send_message(elicit_message, target_agent)
    Runtime->>TargetAgent: process message
    alt TargetAgent is UserProxy
        TargetAgent->>User: request user input
        User->>TargetAgent: user response
    else TargetAgent is LLM Agent
        TargetAgent->>ModelClient: request completion
        ModelClient->>TargetAgent: generated completion
    end
    TargetAgent->>Runtime: Response
    Runtime->>Elicitor: Response
    Elicitor->>ModelClient: Request completion to convert Target Agent response to JSON.
    ModelClient->>Elicitor: JSON formatted response
    Elicitor->>Host: elicit result
    Host->>Workbench: elicit result
    Workbench->>Server: elicit result
    Server->>Workbench: tool result
    Workbench->>Assistant: tool execution result
```

### List Roots Request Flow

```mermaid
sequenceDiagram
    participant Assistant as AutoGen Assistant
    participant Workbench as McpWorkbench
    participant Server as MCP Server
    participant Host as McpSessionHost

    Assistant->>Workbench: call_tool(tool, args)
    Workbench->>Server: execute tool
    Note over Server: Tool needs to know available file system roots
    Server->>Workbench: list_roots request
    Workbench->>Host: handle_list_roots_request()
    Host->>Host: check configured roots
    alt Static roots configured
        Host->>Host: return configured root list
    else Callable roots configured
        Host->>Host: execute callable to get roots
    end
    Host->>Workbench: ListRootsResult
    Workbench->>Server: roots response
    Server->>Workbench: tool result with root info
    Workbench->>Assistant: tool execution result
```

## Components

### McpSessionHost

The main host-side component that handles server-to-host requests and coordinates with AutoGen components:

- **Model Client**: Handles sampling requests using any `ChatCompletionClient`
- **Elicitor**: Routes elicitation requests to a ChatComletionClient or to AutoGen agents for user interaction
- **Roots**: Provides file system access configuration

### Elicitors

Elicitors handle structured prompting requests from MCP servers on the host side:

#### GroupChatAgentElicitor
Routes elicitation requests to specific agents within a group chat, allowing for interactive user input collection through AutoGen agents.

#### ChatCompletionClientElicitor
Handles elicitation requests directly using a language model, suitable for automated structured responses.

## Usage

### Example

```diff
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams
+ from autogen_ext.tools.mcp.host import GroupChatAgentElicitor, McpSessionHost

# Setup model client
model_client = OpenAIChatCompletionClient(model="gpt-4o")

# Create agents
user_proxy = UserProxyAgent("user_proxy")

+ # Create elicitor targeting the user proxy
+ elicitor = GroupChatAgentElicitor("user_proxy", model_client=model_client)

+ # Create host with elicitation support
+ host = McpSessionHost(
+     model_client=model_client,  # For sampling requests
+     elicitor=elicitor,         # For elicitation requests,
+     roots=[
+         mcp_types.Root(uri="file:///workspace", name="Workspace"),
+         mcp_types.Root(uri="file:///docs", name="Documentation"),
+     ]
+ )

# Setup MCP workbench
mcp_workbench = McpWorkbench(
    server_params=StdioServerParams(
        command="python",
        args=["your_mcp_server.py"]
    ),
+     host=host,
)

# Create MCP-enabled assistant
assistant = AssistantAgent(
    "assistant",
    model_client=model_client,
    workbench=mcp_workbench,
)

# Create team and link elicitor
team = RoundRobinGroupChat([assistant, user_proxy])
+ # ⚠️ Critical: Must set_group_chat before team.run**  
+ elicitor.set_group_chat(team)

result = await team.run(task="...")
```
