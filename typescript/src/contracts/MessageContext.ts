import { AgentId, TopicId } from "./IAgentRuntime";

export class MessageContext {
  public readonly messageId: string;
  public readonly cancellation?: AbortSignal;
  public sender?: AgentId;
  public topic?: TopicId;
  public isRpc: boolean = false;

  constructor(messageId: string, cancellation?: AbortSignal) {
    this.messageId = messageId;
    this.cancellation = cancellation;
  }

  static create(cancellation?: AbortSignal): MessageContext {
    return new MessageContext(crypto.randomUUID(), cancellation);
  }
}
