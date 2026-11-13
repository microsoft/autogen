import { IAgentRuntime, AgentId, TopicId } from "../../contracts/IAgentRuntime";
import { MessageContext } from "../../contracts/MessageContext";
import { HostableAgentAdapter } from "./HostableAgentAdapter";
import { GroupChatAgentResponse, GroupChatStart } from "./Events";
import { IGroupChatHandler } from "./GroupChatManagerBase";

/**
 * Configuration for a group chat handler.
 */
export interface GroupChatHandlerConfig {
    /**
     * The topic type to subscribe to
     */
    topicType: string;

    /**
     * The handler for group chat events
     */
    handler: IGroupChatHandler;
}

/**
 * Routes group chat events to appropriate handlers based on topic type.
 */
export class GroupChatHandlerRouter extends HostableAgentAdapter {
    private readonly parentTopic: TopicId;
    private readonly handler: IGroupChatHandler;

    /**
     * Creates a new instance of GroupChatHandlerRouter.
     * @param agentContext The context for agent instantiation
     * @param config The configuration for this handler
     */
    constructor(
        agentId: AgentId,
        runtime: IAgentRuntime,
        config: GroupChatHandlerConfig
    ) {
        super(agentId, runtime, `Router for ${config.topicType}`);
        this.parentTopic = { type: config.topicType, source: this.id.key };
        this.handler = config.handler;

        // Attach the message publisher to the handler
        this.handler.attachMessagePublishServicer(async (event, topicType, cancellation) => {
            // Updated to match IAgentRuntime.publishMessageAsync signature
            await this.runtime.publishMessageAsync(
                event, 
                { type: topicType, source: this.id.key },
                this.id
            );
        });
    }

    /**
     * Handles incoming messages by routing them to the appropriate handler.
     */
    async handleAsync(message: unknown, context: MessageContext): Promise<unknown> {
        if (message instanceof GroupChatStart || message instanceof GroupChatAgentResponse) {
            await this.handler.handleAsync(message, context);
        }
        return null;
    }
}
