import { ChatMessage, StopMessage, AgentMessage } from "../abstractions/Messages";
import { ITerminationCondition } from "../abstractions/Termination";
import { GroupChatOptions } from "./GroupChatOptions";
import { IHandle } from "../../contracts/IHandle";
import { 
    GroupChatEventBase, 
    GroupChatStart, 
    GroupChatAgentResponse, 
    GroupChatRequestPublish, 
    GroupChatMessage, 
    GroupChatTermination, 
    GroupChatReset 
} from "./Events";
import { MessageContext } from "../../contracts/MessageContext";

/**
 * Delegate type for publishing messages.
 */
type MessagePublishServicer = (event: GroupChatEventBase, topicType: string, cancellation?: AbortSignal) => Promise<void>;

/**
 * Interface for handlers that can process group chat events.
 */
export interface IGroupChatHandler {
    /**
     * Attaches a servicer for publishing messages.
     */
    attachMessagePublishServicer(servicer?: MessagePublishServicer): void;

    /**
     * Detaches the current message publishing servicer.
     */
    detachMessagePublishServicer(): void;

    /**
     * Handles group chat messages.
     */
    handleAsync(message: GroupChatStart | GroupChatAgentResponse | unknown, context: MessageContext): Promise<void>;
}

/**
 * Base class for managing group chat interactions.
 */
export abstract class GroupChatManagerBase implements IGroupChatHandler {
    protected readonly options: GroupChatOptions;
    protected messagePublishServicer?: MessagePublishServicer;
    protected messages: AgentMessage[] = []; // Changed from ChatMessage[] to AgentMessage[]
    private readonly terminationCondition?: ITerminationCondition;
    private readonly maxTurns?: number;
    private currentTurn: number = 0;

    constructor(options: GroupChatOptions) {
        this.options = options;
        this.terminationCondition = options.terminationCondition;
        this.maxTurns = options.maxTurns;
    }

    attachMessagePublishServicer(servicer?: MessagePublishServicer): void {
        this.messagePublishServicer = servicer;
    }

    detachMessagePublishServicer(): void {
        this.messagePublishServicer = undefined;
    }

    protected async publishMessageAsync(
        event: GroupChatEventBase,
        topicType: string,
        cancellation?: AbortSignal
    ): Promise<void> {
        if (this.messagePublishServicer) {
            await this.messagePublishServicer(event, topicType, cancellation);
        }
    }

    /**
     * Handles the start of a group chat session.
     */
    async handleAsync(message: GroupChatStart | GroupChatAgentResponse | unknown, context: MessageContext): Promise<void> {
        if (message instanceof GroupChatStart) {
            return this.handleStartAsync(message, context);
        } else if (message instanceof GroupChatAgentResponse) {
            return this.handleResponseAsync(message, context);
        }
        throw new Error(`Unhandled message type: ${typeof message}`);
    }

    protected abstract handleStartAsync(message: GroupChatStart, context: MessageContext): Promise<void>;
    protected abstract handleResponseAsync(message: GroupChatAgentResponse, context: MessageContext): Promise<void>;

    protected async checkTerminationConditionAsync(messages: AgentMessage[]): Promise<StopMessage | null> {
        if (this.maxTurns && ++this.currentTurn >= this.maxTurns) {
            return new StopMessage("Maximum turns reached", "system");
        }

        if (this.terminationCondition) {
            return await this.terminationCondition.checkAndUpdateAsync(messages);
        }

        return null;
    }

    protected async resetAsync(): Promise<void> {
        this.currentTurn = 0;
        this.messages = [];
        this.terminationCondition?.reset();
        
        if (this.messagePublishServicer) {
            await this.messagePublishServicer(
                new GroupChatReset(),
                this.options.groupChatTopicType
            );
        }
    }
}
