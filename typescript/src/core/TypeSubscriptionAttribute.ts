import 'reflect-metadata';
import { ISubscriptionDefinition } from "../contracts/ISubscriptionDefinition";
import { IUnboundSubscriptionDefinition } from "../contracts/IUnboundSubscriptionDefinition";
import { AgentType } from "../contracts/AgentType";
import { TypeSubscription as TypeSubscriptionImpl } from "./TypeSubscription";

/**
 * Decorator factory that creates a subscription for exact topic type matching.
 * @param topic The exact topic type to match against
 * @returns A decorator function that applies subscription metadata to a class
 */
export function TypeSubscription(topic: string): ClassDecorator {
  return function (target: Function): void {
    // Store subscription metadata on the class
    (Reflect as any).defineMetadata('subscription:topic', topic, target);
  };
}

/**
 * An attribute that creates a subscription based on exact topic type matching.
 * This subscription causes each source to have its own agent instance.
 */
export class TypeSubscriptionAttribute implements IUnboundSubscriptionDefinition {
  /**
   * Creates a new instance of TypeSubscriptionAttribute.
   * @param topic The exact topic type to match against
   */
  constructor(private readonly topic: string) {}

  /**
   * Binds the subscription to a specific agent type.
   * @param agentType The agent type to associate with the subscription
   * @returns A concrete subscription definition bound to the specified agent type
   */
  bind(agentType: AgentType): ISubscriptionDefinition {
    return new TypeSubscriptionImpl(this.topic, agentType);
  }
}
