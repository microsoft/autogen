import { BaseAgent } from "../../src/core/BaseAgent";
import { IHandle } from "../../src/contracts/IHandle";
import { AgentId, IAgentRuntime } from "../../src/contracts/IAgentRuntime";
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
    if (typeof message === "string") {
      this.receivedItems.push(message);
      return;
    }

    this.receivedMessages.set(message.source, message.content);
    if ('source' in message && 'content' in message) {
      return message.content;
    }
    return;
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
