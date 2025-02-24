import { describe, it, expect, afterEach, jest } from '@jest/globals';
import { InProcessRuntime } from '../../src/core/InProcessRuntime';
import { TopicId, AgentId, IAgentRuntime } from '../../src/contracts/IAgentRuntime';
import { SubscribedSaveLoadAgent, SubscribedSelfPublishAgent } from './helpers/TestAgent';
import { TextMessage } from './helpers/TestAgent';
import { TypeSubscription, TypeSubscriptionAttribute } from '../../src/core/TypeSubscriptionAttribute';
import { BaseAgent } from '../../src/core/BaseAgent';
import { MessageContext } from '../../src/contracts/MessageContext';

@TypeSubscription("TestTopic")
class SubscribedAgent extends BaseAgent {
    constructor(id: AgentId, runtime: IAgentRuntime) {
        super(id, runtime, "Test Agent");
    }

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
  // Add afterEach cleanup for all tests
  afterEach(async () => {
    // Force cleanup any hanging runtimes
    jest.clearAllTimers();
  });

  it('should not deliver to self by default', async () => {
    const runtime = new InProcessRuntime();
    console.log('Starting runtime...');
    await runtime.start();  // Add explicit start like .NET version

    let agent: SubscribedSelfPublishAgent | undefined;

    // Register and create agent with description
    const agentId = { type: "MyAgent", key: "test" };
    await runtime.registerAgentFactoryAsync("MyAgent", async (id, runtime) => {
      agent = new SubscribedSelfPublishAgent(id, runtime);
      return agent;
    });

    console.log('Agent registered, ensuring creation...');
    await runtime.getAgentMetadataAsync(agentId);
    expect(agent).toBeDefined();
    if (!agent) throw new Error("Agent not initialized");

    console.log('Agent state before subscription:', {
      Text: agent.Text,
      agentId: agent.id
    });

    // Add subscription
    const sub = new TypeSubscriptionAttribute("TestTopic").bind("MyAgent");
    await runtime.addSubscriptionAsync(sub);
    console.log('Added subscription:', {
      id: sub.id,
      agentType: "MyAgent",
      topic: "TestTopic"
    });

    // Send message that will trigger self-publish
    console.log('Sending initial message...');
    await runtime.publishMessageAsync("SelfMessage", { type: "TestTopic", source: "test" });
    await new Promise(resolve => setTimeout(resolve, 100));

    console.log('Final agent state:', {
      Text: agent.Text,
      defaultText: { source: "DefaultTopic", content: "DefaultContent" }
    });

    // Verify the text remains default (self-message wasn't delivered)
    expect(agent.Text.source).toBe("DefaultTopic");
    expect(agent.Text.content).toBe("DefaultContent");

    await runtime.stop(); // Add cleanup
  });

  it('should deliver to self when deliverToSelf is true', async () => {
    const runtime = new InProcessRuntime();
    runtime.deliverToSelf = true;
    await runtime.start(); // Add runtime start
    let agent: SubscribedSelfPublishAgent;

    // Create and register agent
    const agentId = { type: "MyAgent", key: "test" };
    await runtime.registerAgentFactoryAsync("MyAgent", async (id, runtime) => {
      agent = new SubscribedSelfPublishAgent(id, runtime);
      console.log('Created agent:', { id, agent: agent.constructor.name });
      return agent;
    });

    await runtime.getAgentMetadataAsync(agentId); // Ensure agent is created
    console.log('Initial agent state:', { Text: agent!.Text });

    // Add subscription
    await runtime.addSubscriptionAsync(new TypeSubscriptionAttribute("TestTopic").bind("MyAgent"));
    console.log('Added subscription for TestTopic');

    // Send message that will trigger self-publish
    console.log('Publishing message...');
    await runtime.publishMessageAsync("SelfMessage", { type: "TestTopic", source: "test" });
    
    // Wait for message processing to complete - increase timeout since we have cascading messages
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    console.log('Final agent state:', { Text: agent!.Text });
    
    // Verify the text was updated (self-message was delivered)
    expect(agent!.Text.source).toBe("TestTopic");
    expect(agent!.Text.content).toBe("SelfMessage");

    await runtime.stop(); // Add cleanup
  }, 15000);

  // Test for save/load state functionality
  it('should save and load state correctly', async () => {
    // Create first runtime and set up agent
    const runtime = new InProcessRuntime();
    await runtime.start();
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

    await runtime.stop();
    // Also stop the new runtime
    await newRuntime.stop();
  });
});
