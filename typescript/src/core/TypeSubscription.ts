import { ISubscriptionDefinition } from "../contracts/ISubscriptionDefinition";
import { AgentId, TopicId } from "../contracts/IAgentRuntime";
import { AgentType } from "../contracts/AgentType";

export class TypeSubscription implements ISubscriptionDefinition {
  private readonly topicType: string;
  private readonly agentType: AgentType;
  public readonly id: string;

  constructor(topicType: string, agentType?: AgentType, id?: string) {
    this.topicType = topicType;
    this.agentType = agentType || topicType;
    this.id = id ?? crypto.randomUUID();
  }

  matches(topic: TopicId): boolean {
    return topic.type === this.topicType;
  }

  mapToAgent(topic: TopicId): AgentId {
    if (!this.matches(topic)) {
      throw new Error("TopicId does not match the subscription.");
    }
    return { type: this.agentType, key: topic.source };
  }
}
