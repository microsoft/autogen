import { AgentType } from "./AgentType";
import { ISubscriptionDefinition } from "./ISubscriptionDefinition";

export interface IUnboundSubscriptionDefinition {
  bind(agentType: AgentType): ISubscriptionDefinition;
}