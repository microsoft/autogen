import { AgentMessage } from "./Messages";

/**
 * Message indicating that control should be handed off to another agent.
 */
export class HandoffMessage extends AgentMessage {
    /**
     * Gets or sets the target agent to hand off control to.
     */
    targetAgent: string;

    /**
     * Gets or sets an optional message to send to the target agent.
     */
    message?: string;

    constructor(targetAgent: string, message?: string, source?: string) {
        super();
        this.targetAgent = targetAgent;
        this.message = message;
        this.source = source;
    }
}
