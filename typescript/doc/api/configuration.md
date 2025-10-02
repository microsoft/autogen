# Configuration

## Runtime Configuration

Configure the InProcessRuntime:

```typescript
const runtime = new InProcessRuntime();

// Allow agents to receive their own messages
runtime.deliverToSelf = true;

// Start with configured options
await runtime.start();
```

## Agent Configuration 

Configure agent behavior using decorators:

```typescript
import { TypeSubscription, TypePrefixSubscription } from '@microsoft/autogen-ts/core';

// Subscribe to exact topic type
@TypeSubscription("MyTopic")
class MyAgent extends BaseAgent {
  // ...
}

// Subscribe to topic prefix
@TypePrefixSubscription("MyPrefix")
class PrefixAgent extends BaseAgent {
  // ...
}
```

## Message Configuration

Configure message handling:

```typescript
// Configure message context
const context = new MessageContext(messageId);
context.isRpc = true;  // Mark as RPC call
context.sender = { type: "Sender", key: "1" };

// Configure subscriptions
const subscription = new TypeSubscription(
  "MyTopic",    // Topic to match
  "MyAgent",    // Agent type to handle
  "subId123"    // Optional subscription ID
);
```
