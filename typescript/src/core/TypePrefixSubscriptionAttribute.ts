import "reflect-metadata";
import { ISubscriptionDefinition } from "../contracts/ISubscriptionDefinition";
import { IUnboundSubscriptionDefinition } from "../contracts/IUnboundSubscriptionDefinition";
import { AgentType } from "../contracts/AgentType";
import { TypePrefixSubscription as TypePrefixSubscriptionImpl } from "./TypePrefixSubscription";

/**
 * Decorator factory that creates a subscription based on topic type prefix matching.
 * @param topic The topic type prefix to match against
 * @returns A decorator function that applies subscription metadata to a class
 */
export function TypePrefixSubscription(topic: string): ClassDecorator {
  return function (target: Function): void {
    // Store subscription metadata on the class
    (Reflect as any).defineMetadata('subscription:topic:prefix', topic, target);
  };
}

/**
 * An attribute that creates a subscription based on topic type prefix matching.
 * This subscription causes each source to have its own agent instance.
 */
export class TypePrefixSubscriptionAttribute implements IUnboundSubscriptionDefinition {
  /**
   * Creates a new instance of TypePrefixSubscriptionAttribute.
   * @param topic The topic type prefix to match against
   */
  constructor(private readonly topic: string) {}

  /**
   * Binds the subscription to a specific agent type.
   * @param agentType The agent type to associate with the subscription
   * @returns A concrete subscription definition bound to the specified agent type
   */
  bind(agentType: AgentType): ISubscriptionDefinition {
    return new TypePrefixSubscriptionImpl(this.topic, agentType);
  }
}
