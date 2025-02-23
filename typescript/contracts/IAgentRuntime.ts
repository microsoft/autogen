export interface AgentId {
  type: string;
  key: string;
}

export interface TopicId {
  type: string;
  source: string;
}

export interface IAgentRuntime {
  publishMessageAsync(
    message: unknown,
    topic: TopicId,
    sender?: AgentId,
    messageId?: string
  ): Promise<void>;

  sendMessageAsync(
    message: unknown,
    recipient: AgentId,
    sender?: AgentId,
    messageId?: string
  ): Promise<unknown>;

  // ...additional methods from the .NET interface...
}