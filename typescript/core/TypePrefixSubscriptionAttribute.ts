import { ISubscriptionDefinition } from "../contracts/ISubscriptionDefinition";
import { IUnboundSubscriptionDefinition } from "../contracts/IUnboundSubscriptionDefinition";
import { AgentType } from "../contracts/AgentType";
import { TypePrefixSubscription } from "./TypePrefixSubscription";

export class TypePrefixSubscriptionAttribute implements IUnboundSubscriptionDefinition {
  constructor(private readonly topic: string) {}

  bind(agentType: AgentType): ISubscriptionDefinition {
    return new TypePrefixSubscription(this.topic, agentType);
  }
}
