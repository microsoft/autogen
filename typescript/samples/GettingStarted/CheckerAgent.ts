import { BaseAgent } from "../../src/core/BaseAgent";
import { IHandle } from "../../src/contracts/IHandle";
import { MessageContext } from "../../src/contracts/MessageContext";
import { AgentId, IAgentRuntime } from "../../src/contracts/IAgentRuntime";
import { CountMessage, CountUpdate } from "./index";

export class CheckerAgent extends BaseAgent implements IHandle<CountUpdate> {
  constructor(id: AgentId, runtime: IAgentRuntime) {
    super(id, runtime, "Checker Agent");
  }

  async handleAsync(message: CountUpdate, context: MessageContext): Promise<void> {
    console.log(`CheckerAgent received update: ${message.newCount}`);

    if (message.newCount > 1) {
      // Continue the sequence: include both 'count' and 'content'
      const nextCount: CountMessage = { count: message.newCount, content: message.newCount };
      await this.runtime.publishMessageAsync(
        nextCount,
        { type: "CountTopic", source: "checker" }
      );
    } else {
      console.log("Counting complete!");
      process.exit(0);  // End the program when done
    }
  }
}
