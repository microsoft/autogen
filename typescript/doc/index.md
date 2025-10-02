# AutoGen TypeScript Documentation

AutoGen is a framework that enables the development of agent systems using TypeScript. It provides
a flexible, type-safe foundation for building multi-agent applications.

## Getting Started

Install AutoGen TypeScript using npm:

```bash
npm install @microsoft/autogen-ts
```

### Basic Usage

Here's a simple example of creating and using agents:

```typescript
import { AgentsApp } from '@microsoft/autogen-ts';

async function main() {
  const app = await new AgentsAppBuilder()
    .useInProcessRuntime()
    .build();

  await app.start();
  
  try {
    // Create an agent instance
    const agentId = { type: "MyAgent", key: "instance1" };
    await app.runtime.sendMessageAsync(
      { content: "Hello!" },
      agentId
    );
  } finally {
    await app.shutdown();
  }
}
```

## Core Concepts

- [Agents](core/agents.md) - Learn about the agent system
- [Runtime](core/runtime.md) - Understand the runtime environment
- [Subscriptions](core/subscriptions.md) - Explore message routing

## API Documentation

For detailed API documentation, see the [API Reference](api/index.html).
