# Testing Agents

## Unit Testing Agents

Create isolated tests for agent behavior:

```typescript
describe('MyAgent', () => {
  let runtime: InProcessRuntime;
  let agent: MyAgent;

  beforeEach(async () => {
    runtime = new InProcessRuntime();
    await runtime.start();
    
    await runtime.registerAgentFactoryAsync("MyAgent", async (id, rt) => {
      agent = new MyAgent(id, rt);
      return agent;
    });
  });

  afterEach(async () => {
    await runtime.stop();
  });

  it('should handle messages correctly', async () => {
    // Setup
    const agentId = { type: "MyAgent", key: "test" };
    const message = { content: "test" };

    // Act
    const response = await runtime.sendMessageAsync(message, agentId);

    // Assert
    expect(response).toBeDefined();
  });
});
```

## Integration Testing

Test multiple agents working together:

```typescript
describe('Agent Integration', () => {
  it('should coordinate between agents', async () => {
    const app = await new AgentsAppBuilder()
      .useInProcessRuntime()
      .build();
      
    await app.start();
    
    try {
      // Test agent interactions
      await app.runtime.publishMessageAsync(
        { type: "StartProcess" },
        { type: "ProcessEvent", source: "test" }
      );
      
      // Verify results
      // ...
    } finally {
      await app.shutdown();
    }
  });
});
```
