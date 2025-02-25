import { BaseAgent } from "../../src/core/BaseAgent";
import { MessageContext } from "../../src/contracts/MessageContext";
import { CountMessage, CountUpdate } from "./generated/message";
import { TypePrefixSubscription } from "../../src/core/TypePrefixSubscription";

/**
 * Agent that modifies a counter value when it receives a count message.
 */
@TypePrefixSubscription("counter")
export class Modifier extends BaseAgent {
    constructor() {
        super(
            { type: "modifier", key: "default" },
            undefined as any, // Will be set by runtime
            "Agent that modifies counter value"
        );
    }

    async handleAsync(message: unknown, context: MessageContext): Promise<unknown> {
        if (message instanceof CountMessage) {
            const count = message.count + 1;
            console.log(`Modifier: Incrementing count to ${count}`);
            
            await this.runtime.publishMessageAsync(
                new CountUpdate({ newCount: count }),
                { type: "counter.update", source: "modifier" }
            );
            return null;
        }
        
        throw new Error("Unknown message type");
    }
}
