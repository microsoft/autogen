import { AgentMessage, ChatMessage } from './Messages';

/**
 * A valid name for an agent.
 * To ensure parity with Python, we require agent names to be Python identifiers.
 */
export class AgentName {
    // Update regex to be more permissive like C# implementation
    private static readonly NAME_REGEX = /^[\w\s-]+$/;

    constructor(private readonly value: string) {
        AgentName.checkValid(value);
    }

    public static isValid(name: string): boolean {
        return name.length > 0 && this.NAME_REGEX.test(name);
    }

    public static checkValid(name: string): void {
        if (!AgentName.isValid(name)) {
            throw new Error(`Agent name '${name}' is not a valid identifier.`);
        }
    }

    toString(): string {
        return this.value;
    }
}

/**
 * A response from calling IChatAgent's handleAsync.
 */
export interface Response {
    /**
     * A chat message produced by the agent as a response.
     */
    message: ChatMessage;

    /**
     * Inner messages produced by the agent.
     */
    innerMessages?: AgentMessage[];
}

/**
 * Base class for representing a stream of messages interspacing responses and internal processing messages.
 * This functions as a discriminated union.
 */
export class StreamingFrame<TResponse, TInternalMessage extends AgentMessage> {
    public type: 'InternalMessage' | 'Response' = 'Response';  // Set default value
    public internalMessage?: TInternalMessage;
    public response?: TResponse;
}

/**
 * Base class for representing a stream of messages with internal messages of any AgentMessage subtype.
 */
export class BaseStreamingFrame<TResponse> extends StreamingFrame<TResponse, AgentMessage> {}

/**
 * The stream frame for IChatAgent's streamAsync
 */
export class ChatStreamFrame extends BaseStreamingFrame<Response> {}

/**
 * An agent that can participate in a chat.
 */
export interface IChatAgent {
    /**
     * The name of the agent. This is used by team to uniquely identify the agent.
     * It should be unique within the team.
     */
    readonly name: AgentName;

    /**
     * The description of the agent. This is used by team to make decisions about which agents to use.
     * The description should describe the agent's capabilities and how to interact with it.
     */
    readonly description: string;

    /**
     * The types of messages that the agent produces.
     */
    readonly producedMessageTypes: Array<Function>;

    /**
     * Handles chat messages asynchronously and produces a response.
     * @param messages The messages to handle
     * @returns A promise resolving to the response
     */
    handleAsync(messages: ChatMessage[]): Promise<Response>;

    /**
     * Handles chat messages asynchronously and produces a stream of frames.
     * @param messages The messages to handle
     * @returns An async iterable of chat stream frames
     */
    streamAsync(messages: ChatMessage[]): AsyncIterable<ChatStreamFrame>;

    /**
     * Reset the agent to its initialization state.
     */
    resetAsync(): Promise<void>;
}
