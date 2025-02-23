import { BaseAgent } from "../../src/core/BaseAgent";
import { IHandle } from "../../src/contracts/IHandle";
import { AgentId, IAgentRuntime } from "../../src/contracts/IAgentRuntime";
import { MessageContext } from "../../src/contracts/MessageContext";
import { TypeSubscription } from "../../src/core/TypeSubscriptionAttribute";
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
