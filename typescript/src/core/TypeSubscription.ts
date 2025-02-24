import { ISubscriptionDefinition } from "../contracts/ISubscriptionDefinition";
import { AgentId, TopicId } from "../contracts/IAgentRuntime";
import { AgentType } from "../contracts/AgentType";

export class TypeSubscription implements ISubscriptionDefinition {
  public readonly id: string;
  private readonly topicType: string;
  private readonly agentType: AgentType;

  constructor(topicType: string, agentType: AgentType, id?: string) {
    this.topicType = topicType;
    this.agentType = agentType;
    this.id = id ?? crypto.randomUUID();
  }

  matches(topic: TopicId): boolean {
    console.log('TypeSubscription.matches:', {
      topicType: topic.type,
      expectedType: this.topicType,
      match: topic.type === this.topicType
    });
    return topic.type === this.topicType;
  }

  mapToAgent(topic: TopicId): AgentId {
    if (!this.matches(topic)) {
      throw new Error("TopicId does not match the subscription.");
    }
    console.log('TypeSubscription.mapToAgent:', {
      topic,
      agentType: this.agentType,
      result: { type: this.agentType, key: "default" }
    });
    return { 
      type: this.agentType,
      key: "default"  // Always use default key for subscribed agents
    };
  }
}
