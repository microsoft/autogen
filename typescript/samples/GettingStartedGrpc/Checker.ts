import { BaseAgent } from "../../src/core/BaseAgent";
import { MessageContext } from "../../src/contracts/MessageContext";
import { CountMessage } from "./generated/message";
import { CountUpdate } from "./generated/message";

/**
 * Agent that checks and monitors a counter value.
 */
export class Checker extends BaseAgent {
    private count = 0;

    constructor() {
        super(
            { type: "checker", key: "default" },
            undefined as any, // Will be set by runtime
            "Agent that checks counter value"
        );
    }

    async handleAsync(message: unknown, context: MessageContext): Promise<unknown> {
        if (message instanceof CountUpdate) {
            this.count = message.newCount;
            console.log(`Checker: Count is now ${this.count}`);
            return null;
        }
        
        throw new Error("Unknown message type");
    }

    async startCount(): Promise<void> {
        await this.runtime.publishMessageAsync(
            new CountMessage({ count: 0 }),
            { type: "counter", source: "checker" }
        );
    }
}
