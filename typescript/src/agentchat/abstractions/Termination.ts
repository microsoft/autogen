import { AgentMessage, StopMessage } from "./Messages";

/**
 * Exception thrown when a chat has already terminated.
 */
export class TerminatedException extends Error {
    constructor() {
        super("The chat has already terminated.");
        this.name = "TerminatedException";
    }
}

/**
 * Defines a condition that determines when a chat should terminate.
 */
export interface ITerminationCondition {
    /**
     * Gets whether the chat has already terminated.
     */
    readonly isTerminated: boolean;

    /**
     * Checks if new messages should cause termination of the chat.
     * @param messages The messages to check
     * @returns A StopMessage if the chat should terminate, null otherwise
     */
    checkAndUpdateAsync(messages: AgentMessage[]): Promise<StopMessage | null>;

    /**
     * Resets the termination condition to its initial state.
     */
    reset(): void;
}
