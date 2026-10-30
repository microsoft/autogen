import { AgentId, TopicId } from "./IAgentRuntime";

/**
 * Represents the context of a message being sent within the agent runtime.
 * This includes metadata such as the sender, topic, RPC status, and cancellation handling.
 */
export class MessageContext {
  /**
   * Gets the unique identifier for this message.
   */
  public readonly messageId: string;

  /**
   * Gets the cancellation signal associated with this message.
   * This can be used to cancel the operation if necessary.
   */
  public readonly cancellation?: AbortSignal;

  /**
   * Gets or sets the sender of the message.
   * If null, the sender is unspecified.
   */
  public sender?: AgentId;

  /**
   * Gets or sets the topic associated with the message.
   * If null, the message is not tied to a specific topic.
   */
  public topic?: TopicId;

  /**
   * Gets or sets a value indicating whether this message is part of an RPC (Remote Procedure Call).
   */
  public isRpc: boolean = false;

  /**
   * Creates a new instance of the MessageContext class.
   * @param messageId The unique identifier for this message.
   * @param cancellation Optional cancellation signal for the message.
   */
  constructor(messageId: string, cancellation?: AbortSignal) {
    this.messageId = messageId;
    this.cancellation = cancellation;
  }

  /**
   * Creates a new MessageContext with a random UUID and optional cancellation signal.
   * @param cancellation Optional cancellation signal for the message.
   * @returns A new MessageContext instance.
   */
  static create(cancellation?: AbortSignal): MessageContext {
    return new MessageContext(crypto.randomUUID(), cancellation);
  }
}
