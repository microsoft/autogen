import { AgentMessage, ChatMessage, StopMessage } from "../abstractions/Messages";
import { Response } from "../abstractions/ChatAgent";

/**
 * Base class for all group chat events.
 */
export abstract class GroupChatEventBase {}

/**
 * A request to start a group chat.
 */
export class GroupChatStart extends GroupChatEventBase {
    /**
     * An optional list of messages to start the group chat.
     */
    messages?: ChatMessage[];

    constructor(options?: { messages?: ChatMessage[] }) {
        super();
        if (options?.messages) {
            this.messages = options.messages;
        }
    }
}

/**
 * A response published to a group chat.
 */
export class GroupChatAgentResponse extends GroupChatEventBase {
    /**
     * The response from an agent.
     */
    agentResponse!: Response;

    constructor(options: { agentResponse: Response }) {
        super();
        this.agentResponse = options.agentResponse;
    }
}

/**
 * A request to publish a message to a group chat.
 */
export class GroupChatRequestPublish extends GroupChatEventBase {
    messages?: AgentMessage[];

    constructor(options?: { messages?: AgentMessage[] }) {
        super();
        if (options?.messages) {
            this.messages = options.messages;
        }
    }
}

/**
 * A message from a group chat.
 */
export class GroupChatMessage extends GroupChatEventBase {
    /**
     * The message that was published.
     */
    message!: AgentMessage;
}

/**
 * A message indicating that group chat was terminated.
 */
export class GroupChatTermination extends GroupChatEventBase {
    /**
     * The stop message that indicates the reason of termination.
     */
    message!: StopMessage;
}

/**
 * A request to reset the agents in the group chat.
 */
export class GroupChatReset extends GroupChatEventBase {}
