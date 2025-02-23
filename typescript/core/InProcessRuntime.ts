import { IAgentRuntime, AgentId, TopicId } from "../contracts/IAgentRuntime";

interface SubscriptionDefinition {
  id: string;
  matches(topic: TopicId): boolean;
  mapToAgent(topic: TopicId): AgentId;
}

export class InProcessRuntime implements IAgentRuntime {
  public deliverToSelf = false;
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

  public async getAgentMetadataAsync(agentId: AgentId): Promise<unknown> {
    // ...placeholder logic...
    return Promise.resolve(null);
  }

  async loadAgentStateAsync(agentId: AgentId, state: unknown): Promise<void> {
    const agentKey = `${agentId.type}:${agentId.key}`;
    const agent = this.agentInstances.get(agentKey);
    if (!agent) {
      throw new Error(`Agent ${agentKey} not found`);
    }
    // TODO: Implement proper state loading
    return Promise.resolve();
  }

  async saveAgentStateAsync(agentId: AgentId): Promise<unknown> {
    const agentKey = `${agentId.type}:${agentId.key}`;
    const agent = this.agentInstances.get(agentKey);
    if (!agent) {
      throw new Error(`Agent ${agentKey} not found`);
    }
    // TODO: Implement proper state saving
    return Promise.resolve({});
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