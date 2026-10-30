import { BaseAgent } from "../../src/core/BaseAgent";
import { IHandle } from "../../src/contracts/IHandle";
import { MessageContext } from "../../src/contracts/MessageContext";
import { AgentId, IAgentRuntime } from "../../src/contracts/IAgentRuntime";
import { CountMessage, CountUpdate } from "./index";

export class ModifierAgent extends BaseAgent implements IHandle<CountMessage> {
  constructor(id: AgentId, runtime: IAgentRuntime) {
    super(id, runtime, "Modifier Agent");
  }

  async handleAsync(message: CountMessage, context: MessageContext): Promise<void> {
    console.log(`ModifierAgent received count: ${message.count}`);
    
    // Decrement the count
    const newCount = message.count - 1;
    
    // Publish the update
    const update: CountUpdate = { newCount };
    await this.runtime.publishMessageAsync(
      update,
      { type: "UpdateTopic", source: "modifier" }
    );
  }
}
