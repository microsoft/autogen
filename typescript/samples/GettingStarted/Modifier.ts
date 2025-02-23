import { BaseAgent } from "../../core/BaseAgent";
import { IHandle } from "../../contracts/IHandle";
import { AgentId, IAgentRuntime } from "../../contracts/IAgentRuntime";
import { MessageContext } from "../../contracts/MessageContext";
import { TypeSubscription } from "../../core/TypeSubscriptionAttribute";
import { CountMessage } from "./CountMessage";
import { CountUpdate } from "./CountUpdate";

type ModifyF = (x: number) => number;

@TypeSubscription("default")
export class Modifier extends BaseAgent implements IHandle<CountMessage> {
  private modifyFunc: ModifyF;

  constructor(id: AgentId, runtime: IAgentRuntime, modifyFunc: ModifyF) {
    super(id, runtime, "Modifier");
    this.modifyFunc = modifyFunc;
  }

  async handleAsync(message: CountMessage, context: MessageContext): Promise<void> {
    const newValue = this.modifyFunc(message.content);
    console.log(`\nModifier:\nModified ${message.content} to ${newValue}`);

    const updateMessage: CountUpdate = { newCount: newValue };
    await this.runtime.publishMessageAsync(
      updateMessage, 
      { type: "default", source: this.id.key }
    );
  }
}
