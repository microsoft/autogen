import { AgentId, IAgentRuntime } from "../../contracts/IAgentRuntime";
import { MessageContext } from "../../contracts/MessageContext";
import { HostableAgentAdapter } from "./HostableAgentAdapter";
import { GroupChatMessage } from "./Events";
import { AgentMessage } from "../abstractions/Messages";

/**
 * Interface for sinks that can collect output messages.
 */
export interface IOutputCollectionSink {
    /**
     * Called when a message is collected.
     * @param message The collected message
     */
    onMessageCollected(message: AgentMessage): Promise<void>;
}

/**
 * Agent that collects output messages from a group chat.
 */
export class OutputCollectorAgent extends HostableAgentAdapter {
    private readonly sink: IOutputCollectionSink;

    /**
     * Creates a new instance of OutputCollectorAgent.
     */
    constructor(
        agentId: AgentId,
        runtime: IAgentRuntime,
        sink: IOutputCollectionSink,
        description: string = "Collects output messages from the group chat"
    ) {
        super(agentId, runtime, description);
        this.sink = sink;
    }

    /**
     * Handles incoming messages by collecting them via the sink.
     */
    async handleAsync(message: unknown, context: MessageContext): Promise<void> {
        if (message instanceof GroupChatMessage && message.message) {
            await this.sink.onMessageCollected(message.message);
        }
    }
}
