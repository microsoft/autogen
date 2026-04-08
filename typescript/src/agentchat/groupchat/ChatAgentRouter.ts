import { IChatAgent } from "../abstractions/ChatAgent";
import { HostableAgentAdapter } from "./HostableAgentAdapter";
import { AgentId, IAgentRuntime } from "../../contracts/IAgentRuntime";
import { MessageContext } from "../../contracts/MessageContext";
import { GroupChatStart, GroupChatAgentResponse, GroupChatReset, GroupChatRequestPublish } from "./Events";
import { ChatMessage, AgentMessage } from "../abstractions/Messages";

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
    // Add a private messages store
    private messages: AgentMessage[] = [];
    private readonly parentTopic: { type: string; source: string };
    private readonly outputTopic: { type: string; source: string };
    // Store underlying chat agent
    private readonly agent: IChatAgent;

    constructor(agentId: AgentId, runtime: IAgentRuntime, config: AgentChatConfig) {
        super(agentId, runtime, config.chatAgent.description);
        this.parentTopic = { type: config.parentTopicType, source: this.id.key };
        this.outputTopic = { type: config.outputTopicType, source: this.id.key };
        this.agent = config.chatAgent;
    }

    // Add getter for chatAgent
    get chatAgent(): IChatAgent {
        return this.agent;
    }

    async handleAsync(message: unknown, context: MessageContext): Promise<unknown> {
        console.log('ChatAgentRouter.handleAsync:', {
            messageType: message?.constructor.name,
            agentName: this.agent.name.toString(),
            currentMessages: this.messages.length,
            messageDetails: message instanceof ChatMessage ? message.content : undefined
        });

        // Handle reset request
        if (message instanceof GroupChatReset) {
            await this.agent.resetAsync();
            this.messages = []; // Clear messages on reset
            console.log('Reset agent state');
            return null;
        }
        
        // Handle start request
        if (message instanceof GroupChatStart) {
            if (message.messages) {
                this.messages = [...message.messages];
            }
            return null;
        }

        // Handle publish request
        if (message instanceof GroupChatRequestPublish) {
            // Use provided messages, don't overwrite existing ones
            const messagesForAgent = message.messages ?? this.messages;
            
            console.log('Processing messages for publish:', {
                messageCount: messagesForAgent.length,
                messages: messagesForAgent.map(m => ({
                    type: m.constructor.name,
                    content: 'content' in m ? m.content : undefined
                }))
            });

            const chatMessages = messagesForAgent.filter((m): m is ChatMessage => m instanceof ChatMessage);
            const response = await this.chatAgent.handleAsync(chatMessages);
            
            if (response.message) {
                return new GroupChatAgentResponse({ agentResponse: response });
            }
        }
        
        return null;
    }
}
