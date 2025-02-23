import { ISubscriptionDefinition } from "../contracts/ISubscriptionDefinition";
import { IUnboundSubscriptionDefinition } from "../contracts/IUnboundSubscriptionDefinition";
import { AgentType } from "../contracts/AgentType";
import { TypeSubscription } from "./TypeSubscription";

export class TypeSubscriptionAttribute implements IUnboundSubscriptionDefinition {
  constructor(private readonly topic: string) {}

  bind(agentType: AgentType): ISubscriptionDefinition {
    return new TypeSubscription(this.topic, agentType);
  }
}
