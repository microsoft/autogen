import { ITerminationCondition } from "../abstractions/Termination";
import { AgentMessage, StopMessage } from "../abstractions/Messages";

/**
 * Terminate a conversation if a StopMessage is received.
 */
export class StopMessageTermination implements ITerminationCondition {
    private _isTerminated = false;

    /**
     * Gets whether the chat has already terminated.
     */
    get isTerminated(): boolean {
        return this._isTerminated;
    }

    /**
     * Checks if new messages should cause termination of the chat.
     * @param messages The messages to check
     * @returns A StopMessage if a stop message is found, null otherwise
     */
    async checkAndUpdateAsync(messages: AgentMessage[]): Promise<StopMessage | null> {
        const stopMessage = messages.find(m => m instanceof StopMessage) as StopMessage | undefined;
        if (stopMessage) {
            this._isTerminated = true;
        }
        return stopMessage ?? null;
    }

    /**
     * Resets the termination condition to its initial state.
     */
    reset(): void {
        this._isTerminated = false;
    }
}
