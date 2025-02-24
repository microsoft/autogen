import { ISubscriptionDefinition } from "../contracts/ISubscriptionDefinition";
import { AgentId, TopicId } from "../contracts/IAgentRuntime";
import { AgentType } from "../contracts/AgentType";

/**
 * This subscription matches on topics based on a prefix of the type and maps to agents using the source of the topic as the agent key.
 * This subscription causes each source to have its own agent instance.
 * @example
 * ```typescript
 * const subscription = new TypePrefixSubscription("t1", "a1");
 * ```
 * In this case:
 * - A TopicId with type "t1" and source "s1" will be handled by an agent of type "a1" with key "s1"
 * - A TopicId with type "t1" and source "s2" will be handled by an agent of type "a1" with key "s2"
 * - A TopicId with type "t1SUFFIX" and source "s2" will be handled by an agent of type "a1" with key "s2"
 */
export class TypePrefixSubscription implements ISubscriptionDefinition {
  /**
   * The topic type prefix used for matching.
   */
  private readonly topicTypePrefix: string;

  /**
   * The agent type that handles this subscription.
   */
  private readonly agentType: AgentType;

  /**
   * Gets the unique identifier of the subscription.
   */
  public readonly id: string;

  /**
   * Initializes a new instance of the TypePrefixSubscription class.
   * @param topicTypePrefix Topic type prefix to match against
   * @param agentType Agent type to handle this subscription
   * @param id Optional unique identifier for the subscription. If not provided, a new UUID will be generated
   */
  constructor(topicTypePrefix: string, agentType: AgentType, id?: string) {
    this.topicTypePrefix = topicTypePrefix;
    this.agentType = agentType;
    this.id = id ?? crypto.randomUUID();
  }

  /**
   * Checks if a given TopicId matches the subscription based on its type prefix.
   * @param topic The topic to check
   * @returns true if the topic's type starts with the subscription's prefix, false otherwise
   */
  matches(topic: TopicId): boolean {
    return topic.type.startsWith(this.topicTypePrefix);
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
    return { type: this.agentType, key: topic.source };
  }
}
