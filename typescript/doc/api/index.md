# AutoGen TypeScript API Reference

This section contains detailed API documentation for the AutoGen TypeScript implementation.

## Core Packages

### Contracts

The `@microsoft/autogen-ts/contracts` package defines the core interfaces:

- [IAgent](./interfaces/IAgent.html) - Base agent interface
- [IAgentRuntime](./interfaces/IAgentRuntime.html) - Runtime interface
- [IHandle](./interfaces/IHandle.html) - Message handler interface

### Core

The `@microsoft/autogen-ts/core` package contains implementations:

- [BaseAgent](./classes/BaseAgent.html) - Base agent class
- [InProcessRuntime](./classes/InProcessRuntime.html) - In-process runtime
- [TypeSubscription](./classes/TypeSubscription.html) - Subscription implementations

## Using the API

Example showing core API usage:

```typescript
import { BaseAgent, InProcessRuntime } from '@microsoft/autogen-ts/core';
import { IHandle, MessageContext } from '@microsoft/autogen-ts/contracts';

// Create an agent
class MyAgent extends BaseAgent implements IHandle<string> {
  async handleAsync(message: string, context: MessageContext): Promise<void> {
    // Handle the message
  }
}

// Set up runtime
const runtime = new InProcessRuntime();
await runtime.start();

// Register agent
await runtime.registerAgentFactoryAsync("MyAgent", 
  async (id, rt) => new MyAgent(id, rt));
```
