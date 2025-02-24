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
            this.messages = [];
            await this.agent.resetAsync();
            console.log('Reset agent state');
            return null;
        }
        
        // Handle start request
        if (message instanceof GroupChatStart) {
            this.messages = message.messages || [];
            console.log('Started with messages:', {
                count: this.messages.length,
                messages: this.messages.map(m => ({
                    type: m.constructor.name,
                    content: 'content' in m ? m.content : undefined
                }))
            });
            return null;
        }

        // Handle publish request
        if (message instanceof GroupChatRequestPublish) {
            // Use stored messages for agent response
            const chatMessages = this.messages.filter((m): m is ChatMessage => m instanceof ChatMessage);
            console.log('Processing messages:', { 
                count: chatMessages.length,
                messages: chatMessages.map(m => m.content)
            });

            const response = await this.chatAgent.handleAsync(chatMessages);
            
            if (response.message) {
                this.messages.push(response.message);
                console.log('Got agent response:', {
                    type: response.message.constructor.name,
                    content: 'content' in response.message ? response.message.content : undefined,
                    totalMessages: this.messages.length
                });
            }
            
            return new GroupChatAgentResponse({ agentResponse: response });
        }
        
        // For other messages
        if (message instanceof ChatMessage) {
            console.log('Adding chat message:', {
                content: message.content
            });
            this.messages.push(message);
        }
        
        return null;
    }
}
