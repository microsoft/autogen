import { AgentId, TopicId } from "../contracts/IAgentRuntime";
import { ResultSink } from "./ResultSink";
import { MessageContext } from "../contracts/MessageContext";

export class MessageEnvelope {
  private _topic?: TopicId;
  private _sender?: AgentId;
  private _receiver?: AgentId;

  constructor(
    public readonly message: unknown,
    public readonly messageId: string = crypto.randomUUID(),
    public readonly cancellation?: AbortSignal
  ) {}

  withSender(sender?: AgentId): MessageEnvelope {
    this._sender = sender;
    return this;
  }

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

  forPublish(
    topic: TopicId,
    servicer: (envelope: MessageEnvelope, cancellation?: AbortSignal) => Promise<void>
  ): MessageDelivery {
    this._topic = topic;
    return new MessageDelivery(this, servicer);
  }

  get topic(): TopicId | undefined {
    return this._topic;
  }

  get sender(): AgentId | undefined {
    return this._sender;
  }

  get receiver(): AgentId | undefined {
    return this._receiver;
  }
}

export class MessageDelivery {
  constructor(
    public readonly message: MessageEnvelope,
    private readonly servicer: (envelope: MessageEnvelope, cancellation?: AbortSignal) => Promise<void>,
    private readonly resultSink?: ResultSink<unknown>
  ) {}

  get future(): Promise<unknown> {
    return this.resultSink?.future ?? Promise.resolve(null);
  }

  async invokeAsync(cancellation?: AbortSignal): Promise<void> {
    await this.servicer(this.message, cancellation);
  }
}
