import { ITerminationCondition } from "../abstractions/Termination";
import { GroupChatManagerBase } from "./GroupChatManagerBase";
import { GroupChatOptions, GroupParticipant } from "./GroupChatOptions";
import { GroupChatStart, GroupChatAgentResponse, GroupChatRequestPublish } from "./Events";
import { MessageContext } from "../../contracts/MessageContext";
import { ChatMessage } from "../abstractions/Messages";
import { TaskFrame, TaskResult } from "../abstractions/Tasks";
import { ITeam } from "../abstractions/ITeam";

/**
 * A group chat implementation that sends messages to participants in round-robin order.
 */
export class RoundRobinGroupChat extends GroupChatManagerBase implements ITeam {
    public readonly teamId: string = crypto.randomUUID();
    private lastParticipantIndex = -1;

    /**
     * Creates a new instance of RoundRobinGroupChat.
     * @param options Configuration options for the group chat
     */
    constructor(options: GroupChatOptions) {
        super(options);
    }

    protected async handleStartAsync(message: GroupChatStart, context: MessageContext): Promise<void> {
        console.log('RoundRobinGroupChat.handleStartAsync:', {
            hasMessages: !!message.messages,
            messageCount: message.messages?.length ?? 0
        });

        // Reset state
        await this.resetAsync();
        
        // Add initial messages
        if (message.messages) {
            this.messages.push(...message.messages);
            console.log('Added initial messages:', {
                messages: this.messages.map(m => ({
                    type: m.constructor.name,
                    content: 'content' in m ? m.content : undefined
                }))
            });
        }

        // Send initial request to first participant
        await this.publishNextAsync();
    }

    protected async handleResponseAsync(message: GroupChatAgentResponse, context: MessageContext): Promise<void> {
        const response = message.agentResponse;
        
        // Add response message to collection
        if (response.message) {
            this.messages.push(response.message);
            console.log('Added response message:', {
                type: response.message.constructor.name,
                content: 'content' in response.message ? response.message.content : undefined,
                totalMessages: this.messages.length
            });
        }

        // Check termination before continuing
        const stopMessage = await this.checkTerminationConditionAsync(this.messages);
        if (stopMessage) {
            console.log('Got stop message:', {
                content: stopMessage.content
            });
            this.messages.push(stopMessage);
            return;
        }

        // Continue to next participant
        await this.publishNextAsync();
        
        // Wait for message processing
        await new Promise(resolve => setTimeout(resolve, 100));
    }

    private async publishNextAsync(): Promise<void> {
        this.lastParticipantIndex = (this.lastParticipantIndex + 1) % this.options.participants.size;
        const participantEntry = Array.from(this.options.participants.entries())[this.lastParticipantIndex];
        
        if (!participantEntry) {
            throw new Error("No participants available");
        }

        const [name, participant] = participantEntry;
        console.log('Publishing to next participant:', {
            name,
            participantIndex: this.lastParticipantIndex,
            totalParticipants: this.options.participants.size
        });

        await this.publishMessageAsync(
            new GroupChatRequestPublish(),
            participant.topicType
        );
    }

    /**
     * Adds a participant to the group chat.
     * @param name The name of the participant
     * @param participant The participant configuration
     */
    public addParticipant(name: string, participant: GroupParticipant): void {
        this.options.participants.set(name, participant);
    }

    /**
     * Execute the group chat with a starting message.
     * @param startMessage The message to start with
     */
    public async *streamAsync(task: string | unknown, cancellation?: AbortSignal): AsyncIterableIterator<TaskFrame> {
        // Convert task to initial messages if it's a string
        const initialMessages = typeof task === 'string' 
            ? [new ChatMessage(task)]
            : task instanceof ChatMessage 
                ? [task]
                : [];

        // Reset state before starting
        await this.resetAsync();

        // Start group chat with initial messages
        const context = new MessageContext(crypto.randomUUID(), cancellation);
        await this.handleAsync(new GroupChatStart({ messages: initialMessages }), context);

        // Convert messages to frames and yield with TaskResult
        yield new TaskFrame(new TaskResult(this.messages));
    }

    /**
     * Reset the team to its initial state.
     * Made public to implement ITeam interface.
     */
    public override async resetAsync(cancellation?: AbortSignal): Promise<void> {
        await super.resetAsync();
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
