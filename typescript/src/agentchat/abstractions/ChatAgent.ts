import { AgentMessage, ChatMessage } from '../messages/Messages';

/**
 * A valid name for an agent.
 * To ensure parity with Python, we require agent names to be Python identifiers.
 */
export class AgentName {
    private static readonly ID_START_CLASS = /[\p{Lu}\p{Ll}\p{Lt}\p{Lm}\p{Lo}\p{Nl}_\u1185-\u1186\u2118\u212E\u309B-\u309C]/u;
    private static readonly ID_CONTINUE_CLASS = /[\w\p{Nl}\p{Mc}_\u1185-\u1186\u2118\u212E\u309B-\u309C\u00B7\u0387\u1369-\u1371\u19DA\u200C\u200D\u30FB\uFF65]/u;
    private static readonly AGENT_NAME_REGEX = new RegExp(`^${AgentName.ID_START_CLASS.source}${AgentName.ID_CONTINUE_CLASS.source}*$`);

    constructor(private readonly value: string) {
        AgentName.checkValid(value);
    }

    public static isValid(name: string): boolean {
        return AgentName.AGENT_NAME_REGEX.test(name);
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
