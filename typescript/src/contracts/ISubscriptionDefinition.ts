import { AgentId, TopicId } from "./IAgentRuntime";

/**
 * Defines a subscription that matches topics and maps them to agents.
 */
export interface ISubscriptionDefinition {
    /**
     * Gets the unique identifier of the subscription.
     */
    id: string;

    /**
     * Checks if a given TopicId matches the subscription.
     * @param topic The topic to check
     * @returns true if the topic matches the subscription; otherwise, false
     */
    matches(topic: TopicId): boolean;

    /**
     * Maps a TopicId to an AgentId.
     * Should only be called if matches() returns true.
     * @param topic The topic to map
     * @returns The AgentId that should handle the topic
     */
    mapToAgent(topic: TopicId): AgentId;
}