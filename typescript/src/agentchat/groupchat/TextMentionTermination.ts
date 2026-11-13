import { ITerminationCondition } from "../abstractions/Termination";
import { AgentMessage, ChatMessage, StopMessage } from "../abstractions/Messages";

/**
 * Terminates a conversation when specific text is mentioned in a message.
 */
export class TextMentionTermination implements ITerminationCondition {
    private _isTerminated = false;

    /**
     * Creates a new instance of TextMentionTermination.
     * @param searchText The text to search for in messages
     * @param ignoreCase Whether to ignore case when searching
     */
    constructor(
        private readonly searchText: string,
        private readonly ignoreCase: boolean = true
    ) {}

    get isTerminated(): boolean {
        return this._isTerminated;
    }

    async checkAndUpdateAsync(messages: AgentMessage[]): Promise<StopMessage | null> {
        // Only check the last message
        const lastMessage = messages[messages.length - 1];
        if (lastMessage instanceof ChatMessage) {
            const content = this.ignoreCase ? lastMessage.content.toLowerCase() : lastMessage.content;
            const searchFor = this.ignoreCase ? this.searchText.toLowerCase() : this.searchText;
            
            if (content.includes(searchFor)) {
                this._isTerminated = true;
                return new StopMessage(`Found termination text: ${this.searchText}`, lastMessage.source);
            }
        }
        return null;
    }

    reset(): void {
        this._isTerminated = false;
    }
}
