import { AgentId, TopicId } from "../contracts/IAgentRuntime";
import { ResultSink } from "./ResultSink";
import { MessageContext } from "../contracts/MessageContext";

/**
 * Represents a message being sent through the runtime system.
 */
export class MessageEnvelope {
  private _topic?: TopicId;
  private _sender?: AgentId;
  private _receiver?: AgentId;

  /**
   * Creates a new message envelope.
   * @param message The message content
   * @param messageId Optional unique identifier for the message. If not provided, a new UUID will be generated
   * @param cancellation Optional cancellation signal
   */
  constructor(
    public readonly message: unknown,
    public readonly messageId: string = crypto.randomUUID(),
    public readonly cancellation?: AbortSignal
  ) {}

  /**
   * Sets the sender of the message.
   * @param sender The agent sending the message
   * @returns This message envelope instance for method chaining
   */
  withSender(sender?: AgentId): MessageEnvelope {
    this._sender = sender;
    return this;
  }

  /**
   * Prepares the message for sending to a specific agent.
   * @param receiver The agent that should receive the message
   * @param servicer Function that handles the actual message delivery
   * @returns A new MessageDelivery instance configured for sending
   */
  forSend(
    receiver: AgentId,
    servicer: (envelope: MessageEnvelope, cancellation?: AbortSignal) => Promise<unknown>
  ): MessageDelivery {
    this._receiver = receiver;

    const resultSink = new ResultSink<unknown>();
    const boundServicer = async (envelope: MessageEnvelope, cancellation?: AbortSignal) => {
      try {
        const result = await servicer(envelope, cancellation);
        resultSink.setResult(result);
      } catch (error) {
        resultSink.setError(error instanceof Error ? error : new Error(String(error)));
      }
    };

    return new MessageDelivery(this, boundServicer, resultSink);
  }

  /**
   * Prepares the message for publishing to a topic.
   * @param topic The topic to publish to
   * @param servicer Function that handles the actual message publishing
   * @returns A new MessageDelivery instance configured for publishing
   */
  forPublish(
    topic: TopicId,
    servicer: (envelope: MessageEnvelope, cancellation?: AbortSignal) => Promise<void>
  ): MessageDelivery {
    this._topic = topic;
    return new MessageDelivery(this, servicer);
  }

  /** Gets the topic this message is being published to, if any */
  get topic(): TopicId | undefined {
    return this._topic;
  }

  /** Gets the sender of this message, if any */
  get sender(): AgentId | undefined {
    return this._sender;
  }

  /** Gets the receiver of this message, if any */
  get receiver(): AgentId | undefined {
    return this._receiver;
  }
}

/**
 * Represents a message delivery operation, including the message and its handling mechanism.
 */
export class MessageDelivery {
  /**
   * Creates a new message delivery.
   * @param message The message envelope to deliver
   * @param servicer The function that performs the actual delivery
   * @param resultSink Optional sink for capturing the delivery result
   */
  constructor(
    public readonly message: MessageEnvelope,
    private readonly servicer: (envelope: MessageEnvelope, cancellation?: AbortSignal) => Promise<void>,
    private readonly resultSink?: ResultSink<unknown>
  ) {}

  /** Gets the future that will resolve with the delivery result */
  get future(): Promise<unknown> {
    return this.resultSink?.future ?? Promise.resolve(null);
  }

  /**
   * Executes the message delivery.
   * @param cancellation Optional cancellation signal
   */
  async invokeAsync(cancellation?: AbortSignal): Promise<void> {
    await this.servicer(this.message, cancellation);
  }
}
