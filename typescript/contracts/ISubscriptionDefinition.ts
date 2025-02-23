import { AgentId, TopicId } from "./IAgentRuntime";

export interface ISubscriptionDefinition {
  id: string;
  matches(topic: TopicId): boolean;
  mapToAgent(topic: TopicId): AgentId;
}