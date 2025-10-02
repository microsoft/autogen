import { BaseAgent } from "../../../src/core/BaseAgent";
import { IHandle } from "../../../src/contracts/IHandle";
import { AgentId, IAgentRuntime, TopicId } from "../../../src/contracts/IAgentRuntime"; // Add TopicId
import { MessageContext } from "../../../src/contracts/MessageContext";
import { TypeSubscription } from "../../../src/core/TypeSubscriptionAttribute";

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
    super(id, runtime);  // Remove "Test Agent" as it's handled in TestAgent
  }
}

@TypeSubscription("TestTopic")
export class SubscribedSaveLoadAgent extends TestAgent {
  constructor(id: AgentId, runtime: IAgentRuntime) {
    super(id, runtime);  // Remove "Test Agent" as it's handled in TestAgent
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

@TypeSubscription("TestTopic")
export class SubscribedSelfPublishAgent extends BaseAgent implements IHandle<string>, IHandle<TextMessage> {
  private _text: TextMessage = { source: "DefaultTopic", content: "DefaultContent" };

  constructor(id: AgentId, runtime: IAgentRuntime) {
    super(id, runtime, "Test Self-Publishing Agent");
  }

  // Combine the two handleAsync methods using type guards
  async handleAsync(item: string | TextMessage, messageContext: MessageContext): Promise<void> {
    if (typeof item === 'string') {
      const strToText: TextMessage = {
        source: "TestTopic",
        content: item
      };
      await this.runtime.publishMessageAsync(strToText, { type: "TestTopic", source: "test" }, this.id);
    } else {
      this._text = item;
    }
  }

  get Text(): TextMessage {
    return this._text;
  }
}
