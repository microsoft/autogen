import { BaseAgent } from "../../src/core/BaseAgent";
import { IHandle } from "../../src/contracts/IHandle";
import { AgentId, IAgentRuntime, TopicId } from "../../src/contracts/IAgentRuntime"; // Add TopicId
import { MessageContext } from "../../src/contracts/MessageContext";
import { TypeSubscription } from "../../src/core/TypeSubscriptionAttribute";

export interface TextMessage {
  source: string;
  content: string;
}

export interface RpcTextMessage {
  source: string;
  content: string;
}

export class TestAgent extends BaseAgent implements IHandle<TextMessage>, IHandle<string>, IHandle<RpcTextMessage> {
  public receivedItems: unknown[] = [];
  protected receivedMessages: Map<string, unknown> = new Map();

  constructor(id: AgentId, runtime: IAgentRuntime) {
    super(id, runtime, "Test Agent");
  }

  async handleAsync(message: TextMessage | string | RpcTextMessage, context: MessageContext): Promise<unknown> {
    console.log(`TestAgent.handleAsync:`, {
      message,
      context,
      agentId: this.id,
      messageType: typeof message
    });
    
    if (typeof message === "string") {
      console.log('Handling string message');
      this.receivedItems.push(message);
      return message;  // Return the string message for RPC
    }

    if ('source' in message && 'content' in message) {
      console.log(`Handling TextMessage: ${message.source} - ${message.content}`);
      this.receivedMessages.set(message.source, message.content);
      return message.content;  // Return content for RPC
    }
    console.log('Unknown message type');
    return null;
  }

  get ReceivedMessages(): Record<string, unknown> {
    return Object.fromEntries(this.receivedMessages);
  }
}

@TypeSubscription("TestTopic")
export class SubscribedAgent extends TestAgent {
  constructor(id: AgentId, runtime: IAgentRuntime) {
    super(id, runtime);
  }
}

@TypeSubscription("TestTopic")
export class SubscribedSaveLoadAgent extends TestAgent {
  constructor(id: AgentId, runtime: IAgentRuntime) {
    super(id, runtime);
  }

  async saveStateAsync(): Promise<unknown> {
    return this.ReceivedMessages;
  }

  async loadStateAsync(state: unknown): Promise<void> {
    if (typeof state === "object" && state !== null) {
      this.receivedMessages = new Map(Object.entries(state));
    }
  }
}

export class SubscribedSelfPublishAgent extends BaseAgent {
  async handleAsync(item: string, messageContext: MessageContext): Promise<void> {
    const strToText: TextMessage = {
      source: "TestTopic",
      content: item
    };
    // Fix method name to match BaseAgent's method
    await this.runtime.publishMessageAsync(strToText, { type: "TestTopic", source: "test" }, this.id);
  }
}
