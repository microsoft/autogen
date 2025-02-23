import { BaseAgent } from "../../src/core/BaseAgent";
import { IHandle } from "../../src/contracts/IHandle";
import { AgentId, IAgentRuntime } from "../../src/contracts/IAgentRuntime";
import { MessageContext } from "../../src/contracts/MessageContext";
import { TypeSubscription } from "../../src/core/TypeSubscriptionAttribute";
import { CountMessage } from "./CountMessage";
import { CountUpdate } from "./CountUpdate";

type TerminationF = (x: number) => boolean;

@TypeSubscription("default")
export class Checker extends BaseAgent implements IHandle<CountUpdate> {
  private runUntilFunc: TerminationF;
  private shutdown: () => void;

  constructor(
    id: AgentId, 
    runtime: IAgentRuntime, 
    runUntilFunc: TerminationF,
    shutdown: () => void
  ) {
    super(id, runtime, "Checker");
    this.runUntilFunc = runUntilFunc;
    this.shutdown = shutdown;
  }

  async handleAsync(message: CountUpdate, context: MessageContext): Promise<void> {
    if (!this.runUntilFunc(message.newCount)) {
      console.log(`\nChecker:\n${message.newCount} passed the check, continue.`);
      const countMessage: CountMessage = { content: message.newCount };
      await this.runtime.publishMessageAsync(
        countMessage,
        { type: "default", source: this.id.key }
      );
    } else {
      console.log(`\nChecker:\n${message.newCount} failed the check, stopping.`);
      this.shutdown();
    }
  }
}
