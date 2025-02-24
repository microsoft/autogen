# Error Handling

AutoGen provides several exception types for handling common error scenarios.

## Core Exceptions

```typescript
// Agent cannot handle a message type
throw new CantHandleException("Unable to process message format");

// Message cannot be delivered
throw new UndeliverableException("Agent not found");

// Message was dropped
throw new MessageDroppedException("Queue full");
```

## Runtime Error Handling

The runtime handles errors during message processing:

```typescript
try {
  await runtime.sendMessageAsync(message, agentId);
} catch (error) {
  if (error instanceof UndeliverableException) {
    // Handle delivery failure
  } else if (error instanceof CantHandleException) {
    // Handle processing failure
  }
}
```

## Agent Error Handling

Agents should implement proper error handling in their message handlers:

```typescript
async handleAsync(message: unknown, context: MessageContext): Promise<unknown> {
  try {
    // Validate message
    if (!this.canHandle(message)) {
      throw new CantHandleException();
    }
    
    // Process message
    return await this.processMessage(message);
  } catch (error) {
    // Log error and rethrow
    console.error('Error handling message:', error);
    throw error;
  }
}
```
