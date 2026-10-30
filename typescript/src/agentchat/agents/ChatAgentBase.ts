import { AgentName, IChatAgent, Response, ChatStreamFrame } from "../abstractions/ChatAgent";
import { ChatMessage } from "../abstractions/Messages";

/**
 * Base class for a chat agent.
 */
export abstract class ChatAgentBase implements IChatAgent {
    /**
     * Gets the name of the agent. This is used by team to uniquely identify the agent.
     */
    public readonly name: AgentName;

    /**
     * Gets the description of the agent. This is used by team to make decisions about which agents to use.
     */
    public readonly description: string;

    /**
     * Creates a new instance of ChatAgentBase.
     * @param name The name of the agent
     * @param description The description of the agent's capabilities
     */
    constructor(name: string, description: string) {
        this.name = new AgentName(name);
        this.description = description;
    }

    /**
     * Gets the types of messages that the agent produces.
     * Must be implemented by derived classes.
     */
    abstract get producedMessageTypes(): Array<Function>;

    /**
     * Handles chat messages asynchronously and produces a stream of frames.
     * Default implementation wraps handleAsync with a stream that includes any inner messages.
     * @param messages The messages to handle
     * @returns An async iterable of chat stream frames
     */
    async *streamAsync(messages: ChatMessage[]): AsyncIterableIterator<ChatStreamFrame> {
        const response = await this.handleAsync(messages);
        
        // First yield any inner messages if present
        if (response.innerMessages) {
            for (const message of response.innerMessages) {
                yield {
                    type: 'InternalMessage',
                    internalMessage: message
                };
            }
        }

        // Then yield the final response
        yield {
            type: 'Response',
            response: response
        };
    }

    /**
     * Handles chat messages asynchronously and produces a response.
     * Must be implemented by derived classes.
     * @param messages The messages to handle
     * @returns A promise resolving to the response
     */
    abstract handleAsync(messages: ChatMessage[]): Promise<Response>;

    /**
     * Reset the agent to its initialization state.
     * Must be implemented by derived classes.
     */
    abstract resetAsync(): Promise<void>;
}
