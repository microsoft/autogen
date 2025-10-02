# Runtime System

The runtime system manages agent lifecycles, message delivery, and subscriptions.

## InProcess Runtime

```typescript
// Initialize and start the runtime
const runtime = new InProcessRuntime();
await runtime.start();

// Register agent factory
await runtime.registerAgentFactoryAsync(
  "MyAgent", 
  async (id: AgentId, runtime: IAgentRuntime) => {
    return new MyAgent(id, runtime);
  }
);

// Send a direct message (RPC)
const response = await runtime.sendMessageAsync(
  { content: "Hello" },
  { type: "MyAgent", key: "instance1" }
);

// Publish a message to subscribers
await runtime.publishMessageAsync(
  { data: "Update" },
  { type: "UpdateTopic", source: "system" }
);

// Clean up
await runtime.stop();
```

## Message Processing

The runtime processes messages asynchronously in a queue:

1. Messages are added to a delivery queue
2. Messages are processed in order
3. For published messages:
   - All matching subscriptions are found
   - Messages are delivered to matching agents
4. For direct messages:
   - The target agent is located or created
   - The message is delivered and response returned

## Lifecycle Management

```typescript
const runtime = new InProcessRuntime();

// Must start before use
await runtime.start();

// Runtime state can be saved
const state = await runtime.saveAgentStateAsync(agentId);

// State can be restored
await runtime.loadAgentStateAsync(agentId, state);

// Clean up when done
await runtime.stop();
