import 'reflect-metadata';
import { ISubscriptionDefinition } from "../contracts/ISubscriptionDefinition";
import { IUnboundSubscriptionDefinition } from "../contracts/IUnboundSubscriptionDefinition";
import { AgentType } from "../contracts/AgentType";
import { TypeSubscription as TypeSubscriptionImpl } from "./TypeSubscription";

// Export the decorator
export function TypeSubscription(topic: string): ClassDecorator {
  return function (target: Function): void {
    // Store subscription metadata on the class
    (Reflect as any).defineMetadata('subscription:topic', topic, target);
  };
}

export class TypeSubscriptionAttribute implements IUnboundSubscriptionDefinition {
  constructor(private readonly topic: string) {}

  bind(agentType: AgentType): ISubscriptionDefinition {
    return new TypeSubscriptionImpl(this.topic, agentType);
  }
}
