import { AgentType } from "./AgentType";
import { ISubscriptionDefinition } from "./ISubscriptionDefinition";

/**
 * Defines a subscription that is not yet bound to a specific agent type.
 * This interface allows the creation of dynamic subscriptions that can later be associated with an agent.
 */
export interface IUnboundSubscriptionDefinition {
  /**
   * Binds the subscription to a specific agent type, creating a concrete subscription definition.
   * @param agentType The agent type to associate with the subscription
   * @returns A new subscription definition bound to the specified agent type
   */
  bind(agentType: AgentType): ISubscriptionDefinition;
}