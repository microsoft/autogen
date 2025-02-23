import { IAgentRuntime, AgentId, TopicId } from "../contracts/IAgentRuntime";

interface SubscriptionDefinition {
  id: string;
  matches(topic: TopicId): boolean;
  mapToAgent(topic: TopicId): AgentId;
}

export class InProcessRuntime implements IAgentRuntime {
  private subscriptions = new Map<string, SubscriptionDefinition>();
  private agentInstances = new Map<string, unknown>();

  async publishMessageAsync(
    message: unknown,
    topic: TopicId,
    sender?: AgentId,
    messageId?: string
  ): Promise<void> {
    for (const sub of this.subscriptions.values()) {
      if (sub.matches(topic)) {
        const targetAgentId = sub.mapToAgent(topic);
        if (targetAgentId.type === sender?.type && targetAgentId.key === sender?.key) {
          continue;
        }
        await this.dispatchMessageToAgent(message, targetAgentId, messageId);
      }
    }
  }

  async sendMessageAsync(
    message: unknown,
    recipient: AgentId,
    sender?: AgentId,
    messageId?: string
  ): Promise<unknown> {
    return this.dispatchMessageToAgent(message, recipient, messageId);
  }

  private async dispatchMessageToAgent(
    message: unknown,
    agentId: AgentId,
    messageId?: string
  ): Promise<unknown> {
    const agentKey = `${agentId.type}:${agentId.key}`;
    let agent = this.agentInstances.get(agentKey);
    if (!agent) {
      agent = {};
      this.agentInstances.set(agentKey, agent);
    }
    return Promise.resolve(null);
  }
}