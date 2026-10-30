/**
 * Base class for all messages in the agent chat system.
 */
export abstract class AgentMessage {
    /**
     * Gets or sets the source of the message (e.g., agent name, system, user).
     */
    source?: string;
}

/**
 * Represents a basic chat message with text content.
 */
export class ChatMessage extends AgentMessage {
    /**
     * Gets or sets the text content of the message.
     */
    content: string;

    constructor(content: string, source?: string) {
        super();
        this.content = content;
        this.source = source;
    }
}

/**
 * Message indicating that the chat should stop.
 */
export class StopMessage extends AgentMessage {
    /**
     * Gets or sets the reason for stopping.
     */
    content: string;

    constructor(content: string, source?: string) {
        super();
        this.content = content;
        this.source = source;
    }
}

/**
 * Represents metadata about a message exchange.
 */
export class MessageMetadata {
    /**
     * Gets or sets any model parameters used to generate the message.
     */
    modelParameters?: Record<string, unknown>;
}

/**
 * Interface for handlers that need to store message metadata.
 */
export interface IStoreMessageMetadata {
    /**
     * Gets the metadata associated with a message.
     * @param messageId The unique identifier of the message.
     * @returns The metadata associated with the message.
     */
    getMetadata(messageId: string): MessageMetadata | undefined;

    /**
     * Associates metadata with a message.
     * @param messageId The unique identifier of the message.
     * @param metadata The metadata to store.
     */
    setMetadata(messageId: string, metadata: MessageMetadata): void;
}
