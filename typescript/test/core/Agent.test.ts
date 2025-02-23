import { describe, it, expect } from '@jest/globals';
import { InProcessRuntime } from '../../src/core/InProcessRuntime';
import { BaseAgent } from '../../src/core/BaseAgent';
import { AgentId, IAgentRuntime } from '../../src/contracts/IAgentRuntime';
import { MessageContext } from '../../src/contracts/MessageContext';
import { IHandle } from '../../src/contracts/IHandle';
import { TextMessage } from './TestAgent';
import { TypeSubscription } from '../../src/core/TypeSubscription';
import { TestAgent, SubscribedAgent } from './TestAgent';

describe('Agent', () => {
  it('should not receive messages when not subscribed', async () => {
    const runtime = new InProcessRuntime();
    let agent: TestAgent;

    await runtime.registerAgentFactoryAsync("MyAgent", async (id, runtime) => {
      agent = new TestAgent(id, runtime);
      return agent;
    });

    const agentId = { type: "MyAgent", key: "default" };
    const topicType = "TestTopic";

    await runtime.publishMessageAsync(
      { source: topicType, content: "test" }, 
      { type: topicType, source: "test" }
    );

    expect(Object.keys(agent!.ReceivedMessages).length).toBe(0);
  });

  it('should receive messages when subscribed', async () => {
    const runtime = new InProcessRuntime();
    let agent: SubscribedAgent;

    await runtime.registerAgentFactoryAsync("MyAgent", async (id, runtime) => {
      agent = new SubscribedAgent(id, runtime);
      return agent;
    });

    const agentId = { type: "MyAgent", key: "default" };
    await runtime.addSubscriptionAsync(new TypeSubscription("TestTopic", "MyAgent"));

    const topicType = "TestTopic";
    await runtime.publishMessageAsync(
      { source: topicType, content: "test" }, 
      { type: topicType, source: "test" }
    );

    expect(Object.keys(agent!.ReceivedMessages).length).toBe(1);
  });

  it('should return response for sendMessage', async () => {
    const runtime = new InProcessRuntime();
    await runtime.registerAgentFactoryAsync("MyAgent", async (id, runtime) => 
      new TestAgent(id, runtime));

    const agentId = { type: "MyAgent", key: "TestAgent" };

    const response = await runtime.sendMessageAsync(
      { source: "TestTopic", content: "Request" },
      agentId
    );

    expect(response).toBe("Request");
  });

  it('should handle subscribe and remove subscription correctly', async () => {
    class ReceiverAgent extends BaseAgent implements IHandle<string> {
      public receivedItems: string[] = [];

      constructor(id: AgentId, runtime: IAgentRuntime) {
        super(id, runtime, "Receiver Agent");
      }

      async handleAsync(message: string, context: MessageContext): Promise<void> {
        this.receivedItems.push(message);
      }
    }

    const runtime = new InProcessRuntime();
    let agent: ReceiverAgent;

    await runtime.registerAgentFactoryAsync("MyAgent", async (id, runtime) => {
      agent = new ReceiverAgent(id, runtime);
      return agent;
    });

    await runtime.getAgentMetadataAsync({ type: "MyAgent", key: "default" });
    expect(agent!.receivedItems.length).toBe(0);

    const topicType = "TestTopic";
    await runtime.publishMessageAsync("info", { type: topicType, source: "test" });
    expect(agent!.receivedItems.length).toBe(0);

    const subscription = new TypeSubscription(topicType, "MyAgent");
    await runtime.addSubscriptionAsync(subscription);

    await runtime.publishMessageAsync("info", { type: topicType, source: "test" });
    expect(agent!.receivedItems.length).toBe(1);
    expect(agent!.receivedItems[0]).toBe("info");

    await runtime.removeSubscriptionAsync(subscription.id);
    await runtime.publishMessageAsync("info", { type: topicType, source: "test" });
    expect(agent!.receivedItems.length).toBe(1);
  });
});
