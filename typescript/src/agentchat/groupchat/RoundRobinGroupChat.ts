import { ITerminationCondition } from "../abstractions/Termination";
import { GroupChatManagerBase } from "./GroupChatManagerBase";
import { GroupChatOptions, GroupParticipant } from "./GroupChatOptions";
import { GroupChatStart, GroupChatAgentResponse, GroupChatRequestPublish } from "./Events";
import { MessageContext } from "../../contracts/MessageContext";
import { ChatMessage, StopMessage } from "../abstractions/Messages";
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
     * @param speakAgent The agent responsible for speaking
     * @param terminateAgent The agent responsible for terminating
     * @param terminationCondition Optional condition for chat termination
     */
    constructor(
        speakAgent: IChatAgent,
        terminateAgent: IChatAgent,
        terminationCondition?: ITerminationCondition
    ) {
        const options = new GroupChatOptions("chat", "output");
        options.terminationCondition = terminationCondition;
        
        super(options);
        
        // Add participants automatically
        this.addParticipant("speak", new GroupParticipant("test", speakAgent.description));
        this.addParticipant("terminate", new GroupParticipant("test", terminateAgent.description));
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

        // Early return if no response message
        if (!response.message) {
            return;
        }

        // Log state before adding new message
        console.log('Processing agent response:', {
            messageType: response.message.constructor.name,
            messageContent: 'content' in response.message ? response.message.content : undefined,
            currentMessages: this.messages.map(m => ({
                type: m.constructor.name,
                content: 'content' in m ? m.content : undefined
            }))
        });

        // Add response to messages
        this.messages.push(response.message);

        // Log state after adding new message 
        console.log('After adding response:', { 
            messageCount: this.messages.length,
            messages: this.messages.map(m => ({
                type: m.constructor.name, 
                content: 'content' in m ? m.content : undefined
            }))
        });

        // If it's a stop message, just return (but keep the message)
        if (response.message instanceof StopMessage) {
            return;
        }

        // Check termination condition 
        const stopMessage = await this.checkTerminationConditionAsync(this.messages);
        if (stopMessage) {
            this.messages.push(stopMessage);
            return;
        }

        // Continue to next participant
        await this.publishNextAsync();
    }

    private async publishNextAsync(): Promise<void> {
        // Calculate next participant index
        this.lastParticipantIndex = (this.lastParticipantIndex + 1) % this.options.participants.size;
        
        const participantEntry = Array.from(this.options.participants.entries())[this.lastParticipantIndex];
        if (!participantEntry) {
            throw new Error("No participants available");
        }

        const [name, participant] = participantEntry;
        
        // Log state before publishing
        console.log("Publishing to next participant:", {
            participantIndex: this.lastParticipantIndex,
            participantName: name,
            topicType: participant.topicType,
            currentMessageCount: this.messages.length,
            messageTypes: this.messages.map(m => m.constructor.name)
        });

        // Create request with current message collection
        const request = new GroupChatRequestPublish({ messages: [...this.messages] });

        // Publish message and wait for processing
        await this.publishMessageAsync(request, participant.topicType);
        await new Promise(resolve => setTimeout(resolve, 50));
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

        // Wait until we see a StopMessage or no new messages
        while (!this.messages.some(m => m instanceof StopMessage)) {
            const lengthBefore = this.messages.length;
            await new Promise(resolve => setTimeout(resolve, 100));
            if (this.messages.length === lengthBefore) break;
        }

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
