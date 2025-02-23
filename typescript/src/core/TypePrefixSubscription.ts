import { ISubscriptionDefinition } from "../contracts/ISubscriptionDefinition";
import { AgentId, TopicId } from "../contracts/IAgentRuntime";
import { AgentType } from "../contracts/AgentType";

export class TypePrefixSubscription implements ISubscriptionDefinition {
  private readonly topicTypePrefix: string;
  private readonly agentType: AgentType;
  public readonly id: string;

  constructor(topicTypePrefix: string, agentType: AgentType, id?: string) {
    this.topicTypePrefix = topicTypePrefix;
    this.agentType = agentType;
    this.id = id ?? crypto.randomUUID();
  }

  matches(topic: TopicId): boolean {
    return topic.type.startsWith(this.topicTypePrefix);
  }

  mapToAgent(topic: TopicId): AgentId {
    if (!this.matches(topic)) {
      throw new Error("TopicId does not match the subscription.");
    }
    return { type: this.agentType, key: topic.source };
  }
}
