import { IChatAgent } from "../abstractions/ChatAgent";
import { HostableAgentAdapter } from "./HostableAgentAdapter";
import { AgentId, IAgentRuntime } from "../../contracts/IAgentRuntime";
import { MessageContext } from "../../contracts/MessageContext";
import { GroupChatStart, GroupChatAgentResponse, GroupChatReset, GroupChatRequestPublish } from "./Events";
import { ChatMessage } from "../abstractions/Messages";

/**
 * Configuration for a chat agent within a group chat.
 */
export interface AgentChatConfig {
    /** The topic type to subscribe to */
    readonly parentTopicType: string;
    /** The topic type for output */
    readonly outputTopicType: string;
    /** The chat agent to route messages to */
    readonly chatAgent: IChatAgent;
}

/**
 * Routes group chat events to an IChatAgent implementation.
 */
export class ChatAgentRouter extends HostableAgentAdapter {
    private messageBuffer: ChatMessage[] = [];
    private readonly parentTopic: { type: string; source: string };
    private readonly outputTopic: { type: string; source: string };
    private readonly agent: IChatAgent;

    constructor(agentId: AgentId, runtime: IAgentRuntime, config: AgentChatConfig) {
        super(agentId, runtime, config.chatAgent.description);
        this.parentTopic = { type: config.parentTopicType, source: this.id.key };
        this.outputTopic = { type: config.outputTopicType, source: this.id.key };
        this.agent = config.chatAgent;
    }

    async handleAsync(message: unknown, context: MessageContext): Promise<unknown> {
        if (message instanceof GroupChatStart) {
            if (message.messages) {
                this.messageBuffer.push(...message.messages);
            }
        } else if (message instanceof GroupChatAgentResponse) {
            // Store the response message for future context
            if (message.agentResponse.message instanceof ChatMessage) {
                this.messageBuffer.push(message.agentResponse.message);
            }
        } else if (message instanceof GroupChatRequestPublish) {
            const response = await this.agent.handleAsync([...this.messageBuffer]);
            await this.runtime.publishMessageAsync(
                new GroupChatAgentResponse({ agentResponse: response }),
                this.parentTopic,
                this.id
            );
        } else if (message instanceof GroupChatReset) {
            this.messageBuffer = [];
            await this.agent.resetAsync();
        }

        return null;
    }
}
