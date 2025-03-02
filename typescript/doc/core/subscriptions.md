# Subscriptions

Subscriptions define how messages are routed to agents based on topic patterns.

## Types of Subscriptions

### Type Subscription

The simplest subscription matches exact topic types:

```typescript
import { TypeSubscription } from '@microsoft/autogen-ts';

// Direct subscription in code
const subscription = new TypeSubscription("MyTopic", "MyAgent");
await runtime.addSubscriptionAsync(subscription);

// Using decorator
@TypeSubscription("MyTopic")
class MyAgent extends BaseAgent {
  // ...agent implementation...
}
```

### Type Prefix Subscription

Matches topics that start with a specific prefix:

```typescript
import { TypePrefixSubscription } from '@microsoft/autogen-ts';

// Direct subscription in code
const subscription = new TypePrefixSubscription("MyTopic", "MyAgent");
await runtime.addSubscriptionAsync(subscription);

// Using decorator
@TypePrefixSubscription("MyTopic")
class MyAgent extends BaseAgent {
  // ...agent implementation...
}
```

## Message Routing

When a message is published:
1. The runtime checks all subscriptions
2. For each matching subscription:
   - Creates or gets the target agent instance
   - Delivers the message to the agent

## Subscription Lifecycle

```typescript
// Add subscription
const sub = new TypeSubscription("MyTopic", "MyAgent");
await runtime.addSubscriptionAsync(sub);

// Remove subscription
await runtime.removeSubscriptionAsync(sub.id);
```
