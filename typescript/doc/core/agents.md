# Agents

Agents are the fundamental building blocks of AutoGen applications. They are autonomous components that can receive messages, process them, and respond.

## Creating an Agent

To create an agent, extend the `BaseAgent` class and implement `IHandle<T>`:

```typescript
import { BaseAgent } from '@microsoft/autogen-ts';
import { IHandle } from '@microsoft/autogen-ts/contracts';
import { MessageContext } from '@microsoft/autogen-ts/contracts';

@TypeSubscription("MyTopic")
export class MyAgent extends BaseAgent implements IHandle<string> {
  constructor(id: AgentId, runtime: IAgentRuntime) {
    super(id, runtime, "My Custom Agent");
  }

  // handleAsync is required by IHandle<T>
  async handleAsync(message: string, context: MessageContext): Promise<unknown> {
    console.log(`Handling message: ${message}`);
    return message; // Echo back for RPC
  }
}
```

## Message Context

Messages are delivered with a `MessageContext` that provides metadata:

```typescript
async handleAsync(message: unknown, context: MessageContext): Promise<unknown> {
  // Context includes:
  console.log({
    messageId: context.messageId,    // Unique ID for the message
    sender: context.sender,          // AgentId of the sending agent (if any)
    topic: context.topic,           // TopicId for published messages
    isRpc: context.isRpc           // true for direct messages
  });
  return null;
}
```

## State Management

Agents can maintain persistent state by implementing save/load methods:

```typescript
export class StatefulAgent extends BaseAgent {
  private messages: string[] = [];

  async saveStateAsync(): Promise<unknown> {
    return {
      messages: this.messages
    };
  }

  async loadStateAsync(state: unknown): Promise<void> {
    if (typeof state === 'object' && state !== null && 'messages' in state) {
      this.messages = (state as { messages: string[] }).messages;
    }
  }
}
