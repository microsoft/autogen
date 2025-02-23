import "reflect-metadata";
import { ISubscriptionDefinition } from "../contracts/ISubscriptionDefinition";
import { IUnboundSubscriptionDefinition } from "../contracts/IUnboundSubscriptionDefinition";
import { AgentType } from "../contracts/AgentType";
import { TypePrefixSubscription as TypePrefixSubscriptionImpl } from "./TypePrefixSubscription";

// Export the decorator
export function TypePrefixSubscription(topic: string): ClassDecorator {
  return function (target: Function): void {
    // Store subscription metadata on the class
    (Reflect as any).defineMetadata('subscription:topic:prefix', topic, target);
  };
}

export class TypePrefixSubscriptionAttribute implements IUnboundSubscriptionDefinition {
  constructor(private readonly topic: string) {}

  bind(agentType: AgentType): ISubscriptionDefinition {
    return new TypePrefixSubscriptionImpl(this.topic, agentType);
  }
}
