import { ITerminationCondition } from "../abstractions/Termination";
import { GroupChatManagerBase } from "./GroupChatManagerBase";
import { GroupChatOptions } from "./GroupChatOptions";
import { GroupChatStart, GroupChatAgentResponse, GroupChatRequestPublish } from "./Events";
import { MessageContext } from "../../contracts/MessageContext";
import { ChatMessage } from "../abstractions/Messages";

/**
 * A group chat implementation that sends messages to participants in round-robin order.
 */
export class RoundRobinGroupChat extends GroupChatManagerBase {
    private lastParticipantIndex = -1;

    /**
     * Creates a new instance of RoundRobinGroupChat.
     * @param options Configuration options for the group chat
     */
    constructor(options: GroupChatOptions) {
        super(options);
    }

    protected async handleStartAsync(message: GroupChatStart, context: MessageContext): Promise<void> {
        if (message.messages) {
            this.messages.push(...message.messages);
        }

        await this.publishNextAsync();
    }

    protected async handleResponseAsync(message: GroupChatAgentResponse, context: MessageContext): Promise<void> {
        const response = message.agentResponse;
        
        // Add ChatMessage type check
        if (!(response.message instanceof ChatMessage)) {
            throw new Error("Response message must be a ChatMessage");
        }
        
        this.messages.push(response.message);

        if (response.innerMessages) {
            this.messages.push(...response.innerMessages);
        }

        // Check termination condition before continuing
        const stopMessage = await this.checkTerminationConditionAsync(this.messages);
        if (stopMessage) {
            this.messages.push(stopMessage);
            return;
        }

        await this.publishNextAsync();
    }

    private async publishNextAsync(): Promise<void> {
        // Get next participant in round-robin order
        this.lastParticipantIndex = (this.lastParticipantIndex + 1) % this.options.participants.size;
        const participantEntry = Array.from(this.options.participants.entries())[this.lastParticipantIndex];
        if (!participantEntry) {
            throw new Error("No participants available");
        }

        const [name, participant] = participantEntry;
        await this.publishMessageAsync(
            new GroupChatRequestPublish(),
            participant.topicType
        );
    }

    /**
     * Creates a new RoundRobinGroupChat with specified options.
     * @param groupChatTopicType Topic type for group chat messages
     * @param outputTopicType Topic type for output messages
     * @param terminationCondition Optional condition for chat termination
     * @param maxTurns Optional maximum number of turns
     * @returns A configured RoundRobinGroupChat instance
     */
    static create(
        groupChatTopicType: string,
        outputTopicType: string,
        terminationCondition?: ITerminationCondition,
        maxTurns?: number
    ): RoundRobinGroupChat {
        const options = new GroupChatOptions(groupChatTopicType, outputTopicType);
        options.terminationCondition = terminationCondition;
        options.maxTurns = maxTurns;
        return new RoundRobinGroupChat(options);
    }
}
