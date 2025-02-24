import { describe, it, expect } from '@jest/globals';
import { InProcessRuntime } from '../../src/core/InProcessRuntime';
import { TopicId } from '../../src/contracts/IAgentRuntime';
import { SubscribedSaveLoadAgent } from './TestAgent';
import { TextMessage } from './TestAgent';
import { TypeSubscription, TypeSubscriptionAttribute } from '../../src/core/TypeSubscriptionAttribute';
import { BaseAgent } from '../../src/core/BaseAgent';
import { MessageContext } from '../../src/contracts/MessageContext';

@TypeSubscription("TestTopic")
class SubscribedAgent extends BaseAgent {
    async handleAsync(message: unknown, context: MessageContext): Promise<unknown> {
        return null;
    }
}

@TypeSubscription("TestTopic")
class AnotherSubscribedAgent extends BaseAgent {
    async handleAsync(message: unknown, context: MessageContext): Promise<unknown> {
        return null;
    }
}

@TypeSubscription("TestTopic")
class ThirdSubscribedAgent extends BaseAgent {
    async handleAsync(message: unknown, context: MessageContext): Promise<unknown> {
        return null;
    }
}

describe('InProcessRuntime', () => {
  it('should not deliver to self by default', async () => {
    const runtime = new InProcessRuntime();
    let agent: SubscribedSaveLoadAgent | undefined;  // Change to allow undefined

    // Register and create agent
    const agentId = { type: "MyAgent", key: "default" };
    await runtime.registerAgentFactoryAsync("MyAgent", async (id, runtime) => {
      agent = new SubscribedSaveLoadAgent(id, runtime);
      return agent;
    });

    // Ensure agent is created before proceeding
    await runtime.getAgentMetadataAsync(agentId);
    expect(agent).toBeDefined();
    if (!agent) throw new Error("Agent not initialized"); // Type guard for TypeScript

    // Add subscription and verify it's added
    await runtime.addSubscriptionAsync(new TypeSubscriptionAttribute("TestTopic").bind("MyAgent"));

    const topicId: TopicId = { type: "TestTopic", source: "test" };
    const message: TextMessage = { source: "TestTopic", content: "test" };
    
    // Send message and wait for processing
    await runtime.publishMessageAsync(message, topicId);
    await new Promise(resolve => setTimeout(resolve, 100));

    // Verify no messages were delivered
    expect(Object.keys(agent!.ReceivedMessages).length).toBe(0);
  });

  it('should deliver to self when deliverToSelf is true', async () => {
    const runtime = new InProcessRuntime();
    runtime.deliverToSelf = true;
    let agent: SubscribedSaveLoadAgent;

    // Create and register agent
    const agentId = { type: "MyAgent", key: "default" };
    await runtime.registerAgentFactoryAsync("MyAgent", async (id, runtime) => {
      agent = new SubscribedSaveLoadAgent(id, runtime);
      return agent;
    });
    
    // Ensure agent exists
    await runtime.getAgentMetadataAsync(agentId);
    
    // Add subscription
    const subscription = new TypeSubscriptionAttribute("TestTopic").bind("MyAgent");
    await runtime.addSubscriptionAsync(subscription);

    // Send message with explicit sender ID
    const topicId: TopicId = { type: "TestTopic", source: "test" };
    const message: TextMessage = { source: "TestTopic", content: "test" };
    await runtime.publishMessageAsync(message, topicId, agentId);
    
    // Wait for message processing and verify
    await new Promise(resolve => setTimeout(resolve, 500));

    console.log('Test verification:', {
      agentMessages: agent!.ReceivedMessages,
      messageLength: Object.keys(agent!.ReceivedMessages).length
    });

    expect(Object.keys(agent!.ReceivedMessages).length).toBe(1);
  });

  // Test for save/load state functionality
  it('should save and load state correctly', async () => {
    // Create first runtime and set up agent
    const runtime = new InProcessRuntime();
    let agent: SubscribedSaveLoadAgent;

    await runtime.registerAgentFactoryAsync("MyAgent", async (id, runtime) => {
      agent = new SubscribedSaveLoadAgent(id, runtime);
      return agent;
    });

    const agentId = { type: "MyAgent", key: "default" };
    await runtime.addSubscriptionAsync(new TypeSubscriptionAttribute("TestTopic").bind("MyAgent"));

    // Send a message to create some state
    const message: TextMessage = { source: "TestTopic", content: "test" };
    await runtime.publishMessageAsync(message, { type: "TestTopic", source: "test" });

    // Save state
    const savedState = await runtime.saveAgentStateAsync(agentId);
    expect(savedState).toBeDefined();

    // Create new runtime and restore state
    const newRuntime = new InProcessRuntime();
    let newAgent: SubscribedSaveLoadAgent;

    await newRuntime.registerAgentFactoryAsync("MyAgent", async (id, runtime) => {
      newAgent = new SubscribedSaveLoadAgent(id, runtime);
      return newAgent;
    });

    // Load the saved state
    await newRuntime.loadAgentStateAsync(agentId, savedState);

    // Verify state was restored
    expect(newAgent!.ReceivedMessages).toEqual(agent!.ReceivedMessages);
  });
});
