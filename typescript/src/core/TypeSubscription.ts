import { ISubscriptionDefinition } from "../contracts/ISubscriptionDefinition";
import { AgentId, TopicId } from "../contracts/IAgentRuntime";
import { AgentType } from "../contracts/AgentType";

/**
 * This subscription matches on topics based on the exact type and maps to agents using the source of the topic as the agent key.
 * This subscription causes each source to have its own agent instance.
 * @example
 * ```typescript
 * const subscription = new TypeSubscription("t1", "a1");
 * ```
 * In this case:
 * - A TopicId with type "t1" and source "s1" will be handled by an agent of type "a1" with key "s1"
 * - A TopicId with type "t1" and source "s2" will be handled by an agent of type "a1" with key "s2"
 */
export class TypeSubscription implements ISubscriptionDefinition {
  /**
   * Gets the unique identifier of the subscription.
   */
  public readonly id: string;

  /**
   * The exact topic type used for matching.
   */
  private readonly topicType: string;

  /**
   * The agent type that handles this subscription.
   */
  private readonly agentType: AgentType;

  /**
   * Initializes a new instance of the TypeSubscription class.
   * @param topicType The exact topic type to match against
   * @param agentType Agent type to handle this subscription
   * @param id Optional unique identifier for the subscription. If not provided, a new UUID will be generated
   */
  constructor(topicType: string, agentType: AgentType, id?: string) {
    this.topicType = topicType;
    this.agentType = agentType;
    this.id = id ?? crypto.randomUUID();
  }

  /**
   * Checks if a given TopicId matches the subscription based on an exact type match.
   * @param topic The topic to check
   * @returns true if the topic's type matches exactly, false otherwise
   */
  matches(topic: TopicId): boolean {
    console.log('TypeSubscription.matches:', {
      topicType: topic.type,
      expectedType: this.topicType,
      match: topic.type === this.topicType
    });
    return topic.type === this.topicType;
  }

  /**
   * Maps a TopicId to an AgentId. Should only be called if matches() returns true.
   * @param topic The topic to map
   * @returns An AgentId representing the agent that should handle the topic
   * @throws Error if the topic does not match the subscription
   */
  mapToAgent(topic: TopicId): AgentId {
    if (!this.matches(topic)) {
      throw new Error("TopicId does not match the subscription.");
    }
    console.log('TypeSubscription.mapToAgent:', {
      topic,
      agentType: this.agentType,
      result: { type: this.agentType, key: topic.source } // Use topic.source instead of "default"
    });
    return { 
      type: this.agentType,
      key: topic.source  // Key change: use topic.source instead of hardcoding "default"
    };
  }
}
