# Messages and Message Handling

## Message Types

Messages in AutoGen can be any serializable type. Common patterns include:

```typescript
// Simple text message
interface TextMessage {
  content: string;
}

// Structured command
interface Command {
  action: string;
  parameters: Record<string, unknown>;
}

// RPC request/response
interface RpcRequest<T> {
  method: string;
  params: T;
}
```

## Message Context

Each message includes context information:

```typescript
const context = new MessageContext(messageId);
context.sender = { type: "SenderAgent", key: "instance1" };
context.topic = { type: "UpdateTopic", source: "system" };
context.isRpc = true;
```

## Message Flow

1. **Direct Messages (RPC)**
   ```typescript
   // Send message and await response
   const response = await runtime.sendMessageAsync(
     { method: "getData", params: { id: 123 } },
     { type: "DataAgent", key: "default" }
   );
   ```

2. **Published Messages**
   ```typescript
   // Publish to all subscribers
   await runtime.publishMessageAsync(
     { event: "dataChanged" },
     { type: "DataEvents", source: "system" }
   );
   ```
