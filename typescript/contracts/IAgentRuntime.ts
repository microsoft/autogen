import { AgentType } from "./AgentType";
import { IAgent } from "./IAgent";
import { ISubscriptionDefinition } from "./ISubscriptionDefinition";

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

  getAgentMetadataAsync(agentId: AgentId): Promise<unknown>;

  loadAgentStateAsync(agentId: AgentId, state: unknown): Promise<void>;
  saveAgentStateAsync(agentId: AgentId): Promise<unknown>;

  registerAgentFactoryAsync(
    type: AgentType,
    factoryFunc: (agentId: AgentId, runtime: IAgentRuntime) => Promise<IAgent>
  ): Promise<AgentType>;

  addSubscriptionAsync(subscription: ISubscriptionDefinition): Promise<void>;
}