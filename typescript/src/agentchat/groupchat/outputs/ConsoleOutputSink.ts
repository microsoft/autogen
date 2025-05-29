import { AgentMessage, ChatMessage } from "../../abstractions/Messages";
import { IOutputCollectionSink } from "../OutputCollectorAgent";

/**
 * A simple output sink that writes messages to the console.
 */
export class ConsoleOutputSink implements IOutputCollectionSink {
    /**
     * Called when a message is collected.
     * @param message The collected message
     */
    async onMessageCollected(message: AgentMessage): Promise<void> {
        if (message instanceof ChatMessage) {
            console.log(`[${message.source ?? 'unknown'}]: ${message.content}`);
        }
    }
}
