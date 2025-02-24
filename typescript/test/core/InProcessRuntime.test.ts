import { describe, it, expect } from '@jest/globals';
import { InProcessRuntime } from '../../src/core/InProcessRuntime';
import { TopicId, AgentId, IAgentRuntime } from '../../src/contracts/IAgentRuntime';
import { SubscribedSaveLoadAgent, SubscribedSelfPublishAgent } from './TestAgent';
import { TextMessage } from './TestAgent';
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
  it('should not deliver to self by default', async () => {
    const runtime = new InProcessRuntime();
    let agent: SubscribedSelfPublishAgent | undefined;

    // Register and create agent with description
    const agentId = { type: "MyAgent", key: "test" };
    await runtime.registerAgentFactoryAsync("MyAgent", async (id, runtime) => {
      agent = new SubscribedSelfPublishAgent(id, runtime);
      return agent;
    });

    // Ensure agent is created
    await runtime.getAgentMetadataAsync(agentId);
    expect(agent).toBeDefined();
    if (!agent) throw new Error("Agent not initialized");

    // Add subscription
    await runtime.addSubscriptionAsync(new TypeSubscriptionAttribute("TestTopic").bind("MyAgent"));

    // Send message that will trigger self-publish
    await runtime.publishMessageAsync("SelfMessage", { type: "TestTopic", source: "test" });
    await new Promise(resolve => setTimeout(resolve, 100));

    // Verify the text remains default (self-message wasn't delivered)
    expect(agent.Text.source).toBe("DefaultTopic");
    expect(agent.Text.content).toBe("DefaultContent");
  });

  it('should deliver to self when deliverToSelf is true', async () => {
    const runtime = new InProcessRuntime();
    runtime.deliverToSelf = true;
    let agent: SubscribedSelfPublishAgent;

    // Create and register agent
    const agentId = { type: "MyAgent", key: "test" };
    await runtime.registerAgentFactoryAsync("MyAgent", async (id, runtime) => {
      agent = new SubscribedSelfPublishAgent(id, runtime);
      return agent;
    });

    // Add subscription
    await runtime.addSubscriptionAsync(new TypeSubscriptionAttribute("TestTopic").bind("MyAgent"));

    // Send message that will trigger self-publish
    await runtime.publishMessageAsync("SelfMessage", { type: "TestTopic", source: "test" });
    await new Promise(resolve => setTimeout(resolve, 500));

    // Verify the text was updated (self-message was delivered)
    expect(agent!.Text.source).toBe("TestTopic");
    expect(agent!.Text.content).toBe("SelfMessage");
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
