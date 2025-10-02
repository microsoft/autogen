import { describe, it, expect } from '@jest/globals';
import { InProcessRuntime } from '../../src/core/InProcessRuntime';
import { BaseAgent } from '../../src/core/BaseAgent';
import { AgentId, IAgentRuntime } from '../../src/contracts/IAgentRuntime';
import { MessageContext } from '../../src/contracts/MessageContext';
import { IHandle } from '../../src/contracts/IHandle';
import { TextMessage, RpcTextMessage } from './helpers/TestAgent';
import { TypeSubscription } from '../../src/core/TypeSubscription';
import { TestAgent, SubscribedAgent } from './helpers/TestAgent';

describe('Agent', () => {
  it('should not receive messages when not subscribed', async () => {
    const runtime = new InProcessRuntime();
    await runtime.start();
    let agent: TestAgent;

    await runtime.registerAgentFactoryAsync("MyAgent", async (id, runtime) => {
      agent = new TestAgent(id, runtime);
      return agent;
    });

    // Ensure agent is created
    await runtime.getAgentMetadataAsync({ type: "MyAgent", key: "default" });

    const topicType = "TestTopic";
    await runtime.publishMessageAsync(
      { source: topicType, content: "test" }, 
      { type: topicType, source: "test" }
    );

    // Wait for message processing
    await new Promise(resolve => setTimeout(resolve, 100));
    expect(Object.keys(agent!.ReceivedMessages).length).toBe(0);

    await runtime.stop(); // Add cleanup
  });

  it('should receive messages when subscribed', async () => {
    const runtime = new InProcessRuntime();
    await runtime.start();
    let agent: SubscribedAgent;

    await runtime.registerAgentFactoryAsync("MyAgent", async (id, runtime) => {
      agent = new SubscribedAgent(id, runtime);
      return agent;
    });

    // Create and get agent
    const agentId = { type: "MyAgent", key: "default" };
    await runtime.getAgentMetadataAsync(agentId);

    // Add subscription and wait for setup
    const subscription = new TypeSubscription("TestTopic", "MyAgent");
    await runtime.addSubscriptionAsync(subscription);

    const topicType = "TestTopic";
    const message = { source: topicType, content: "test" };
    await runtime.publishMessageAsync(message, { type: topicType, source: "test" });

    // Wait longer for message processing
    await new Promise(resolve => setTimeout(resolve, 500));
    expect(Object.keys(agent!.ReceivedMessages).length).toBe(1);

    await runtime.stop();
  }, 15000);

  it('should return response for sendMessage', async () => {
    const runtime = new InProcessRuntime();
    await runtime.start();
    console.log('Runtime started');

    let agent: TestAgent;
    await runtime.registerAgentFactoryAsync("MyAgent", async (id, runtime) => {
      agent = new TestAgent(id, runtime);
      console.log('Created test agent:', { id, agentType: agent.constructor.name });
      return agent;
    });

    const agentId = { type: "MyAgent", key: "test" };
    await runtime.getAgentMetadataAsync(agentId);
    console.log('Agent metadata retrieved');

    const message: RpcTextMessage = { source: "TestTopic", content: "Request" };
    console.log('Sending RPC message:', message);

    const response = await runtime.sendMessageAsync(message, agentId);
    console.log('RPC response received:', response);

    expect(response).toBe("Request");

    await runtime.stop();
  }, 15000);

  it('should handle subscribe and remove subscription correctly', async () => {
    class ReceiverAgent extends BaseAgent implements IHandle<string> {
      public receivedItems: string[] = [];

      constructor(id: AgentId, runtime: IAgentRuntime) {
        super(id, runtime, "Receiver Agent");
      }

      async handleAsync(message: string, context: MessageContext): Promise<unknown> {
        console.log('ReceiverAgent handling message:', { message, context });
        this.receivedItems.push(message);
        return message;
      }
    }

    const runtime = new InProcessRuntime();
    await runtime.start();
    let agent: ReceiverAgent;

    await runtime.registerAgentFactoryAsync("MyAgent", async (id, runtime) => {
      agent = new ReceiverAgent(id, runtime);
      return agent;
    });

    // Ensure agent exists before proceeding
    const agentId = { type: "MyAgent", key: "default" };
    await runtime.getAgentMetadataAsync(agentId);

    // Add subscription and verify it's added
    const topicType = "TestTopic";
    const subscription = new TypeSubscription(topicType, "MyAgent");
    await runtime.addSubscriptionAsync(subscription);
    
    console.log('Publishing message...', { topicType });
    await runtime.publishMessageAsync("info", { type: topicType, source: "test" });
    
    // Wait for message processing
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    console.log('Checking received items:', {
      receivedItems: agent!.receivedItems,
      subscriptions: Array.from(runtime['subscriptions'].entries())
    });
    
    expect(agent!.receivedItems.length).toBe(1);
    expect(agent!.receivedItems[0]).toBe("info");
    
    // Remove subscription and verify no new messages received
    await runtime.removeSubscriptionAsync(subscription.id);
    await runtime.publishMessageAsync("info2", { type: topicType, source: "test" });
    await new Promise(resolve => setTimeout(resolve, 500));
    
    expect(agent!.receivedItems.length).toBe(1);

    await runtime.stop();
  }, 15000);
});
