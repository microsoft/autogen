# Dependency Injection

AutoGen TypeScript supports dependency injection through the AgentsApp builder pattern.

## Basic Setup

```typescript
import { AgentsAppBuilder } from '@microsoft/autogen-ts';

// Create a builder and configure DI
const builder = new AgentsAppBuilder();

// Register dependencies
builder.services.addSingleton<ILogger>(new ConsoleLogger());
builder.services.addScoped<IDatabase>(DatabaseService);

// Build and run the app
const app = await builder.build();
await app.start();
```

## Using Dependencies in Agents

```typescript
export class DatabaseAgent extends BaseAgent {
  constructor(
    id: AgentId, 
    runtime: IAgentRuntime,
    private readonly db: IDatabase // Injected dependency
  ) {
    super(id, runtime, "Database Agent");
  }
  
  async handleAsync(message: unknown, context: MessageContext): Promise<unknown> {
    // Use injected database
    return await this.db.query(message);
  }
}
```
