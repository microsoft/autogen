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
    
    %% Abstract components
    subgraph Abstract_Components ["Abstract Components"]
        R[RootsProvider]
        S[Sampler]
        E[Elicitor Type]
    end

    %% Concrete components
    subgraph Component_Subclasses ["Concrete Components"]
        CCCS[ChatCompletionClientSampler]
        SE[StdioElicitor]
        SRP[StaticRootsProvider]
    end
  end


  %% Server layer: tool execution
  subgraph MCP_Server ["MCP Server"]
    MS[MCP Server]
  end

  %% Chat Completion Client
  CCC[Chat Completion Client]

  %% Flows
  WB -->|tool call| MS
  MS -.->|sampling/elicitation/roots requests| WB

  WB -->|sampling/elicitation/roots requests| HS

  %% Sampling via Sampler
  HS -->|sampling| S
  S --> CCCS
  CCCS -->|completion| CCC

  %% Elicitation via Elicitor
  HS -->|elicitation| E
  E --> SE
  SE -->|stdio| U["User"]

  %% Roots via RootsProvider
  HS -->|roots| R
  R --> SRP
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
    participant Sampler as ChatCompletionClientSampler
    participant ModelClient as ChatCompletionClient

    Assistant->>Workbench: call_tool(tool, args)
    Workbench->>Server: execute tool
    Note over Server: Tool execution requires text generation
    Server->>Workbench: sampling request
    Workbench->>Host: handle_sampling_request()
    Host->>Sampler: sample(params)
    Sampler->>ModelClient: create(messages, extra_args)
    ModelClient->>Sampler: response with content
    Sampler->>Host: CreateMessageResult
    Host->>Workbench: CreateMessageResult
    Workbench->>Server: sampling response
    Server->>Workbench: tool result
    Workbench->>Assistant: tool execution result
```

### Elicitation Request Flow

```mermaid
sequenceDiagram
    participant Assistant as AutoGen Assistant
    participant Workbench as McpWorkbench
    participant Server as MCP Server
    participant Host as McpSessionHost
    participant Elicitor as StdioElicitor
    participant User

    Assistant->>Workbench: call_tool(tool, args)
    Workbench->>Server: execute tool
    Note over Server: Tool needs user input with structured response
    Server->>Workbench: ElicitRequest
    Workbench->>Host: handle_elicit_request()
    Host->>Elicitor: elicit(params)
    Elicitor->>User: prompt via stdio
    User->>Elicitor: response via stdio
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
    participant RootsProvider as StaticRootsProvider

    Assistant->>Workbench: call_tool(tool, args)
    Workbench->>Server: execute tool
    Note over Server: Tool needs to know available file system roots
    Server->>Workbench: list_roots request
    Workbench->>Host: handle_list_roots_request()
    Host->>RootsProvider: list_roots()
    RootsProvider->>Host: ListRootsResult with configured roots
    Host->>Workbench: ListRootsResult
    Workbench->>Server: roots response
    Server->>Workbench: tool result with root info
    Workbench->>Assistant: tool execution result
```

## Components

### McpSessionHost

The main host-side component that handles server-to-host requests and coordinates with component providers:

- **Sampler**: Handles sampling requests via `Sampler`s (e.g. `ChatCompletionClientSampler`)
- **Elicitor**: Handles elicitation requests via `Elicitor`s (e.g. `StdioElicitor`, `StreamElicitor`)
- **RootsProvider**: Provides file system access configuration via `RootsProvider`s (e.g. `StaticRootsProvider`)

### Component Types

#### Samplers
Handle text generation requests from MCP servers:
- **ChatCompletionClientSampler**: Routes sampling requests to any `ChatCompletionClient`

#### Elicitors
Handle structured prompting requests from MCP servers:
- **StdioElicitor**: Interactive user prompting via standard input/output streams.
- **StreamElicitor**: Base class for stream-based elicitation

#### RootsProviders
Manage file system root access for MCP servers:
- **StaticRootsProvider**: Provides a static list of file system roots

## Usage

### Example

```diff
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.tools.mcp import McpWorkbench, StdioServerParams
+ from autogen_ext.tools.mcp import (
+     ChatCompletionClientSampler,
+     McpSessionHost,
+     StaticRootsProvider,
+     StdioElicitor,
+ )
+ from pydantic import FileUrl
+ from mcp.types import Root

# Setup model client
model_client = OpenAIChatCompletionClient(model="gpt-4o")

+ # Create components
+ sampler = ChatCompletionClientSampler(model_client)
+ elicitor = StdioElicitor()
+ roots = StaticRootsProvider([
+     Root(uri=FileUrl("file:///workspace"), name="Workspace"),
+     Root(uri=FileUrl("file:///docs"), name="Documentation"),
+ ])

+ # Create host with all capabilities
+ host = McpSessionHost(
+     sampler=sampler,    # For sampling requests
+     elicitor=elicitor,  # For elicitation requests
+     roots=roots,        # For roots requests
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
```
