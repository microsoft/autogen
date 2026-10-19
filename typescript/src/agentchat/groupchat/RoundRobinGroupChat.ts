import { ITerminationCondition } from "../abstractions/Termination";
import { IChatAgent } from "../abstractions/ChatAgent"; // Add this import
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
    private readonly speakAgent: IChatAgent;
    private readonly terminateAgent: IChatAgent;
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
        
        this.speakAgent = speakAgent;
        this.terminateAgent = terminateAgent;
        
        // Add participants for tracking order
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
        this.lastParticipantIndex = (this.lastParticipantIndex + 1) % this.options.participants.size;
        
        // Get current agent
        const currentAgent = this.lastParticipantIndex === 0 ? this.speakAgent : this.terminateAgent;
        
        // Get chat messages only
        const chatMessages = this.messages.filter((m): m is ChatMessage => m instanceof ChatMessage);
        
        // Call agent directly
        const response = await currentAgent.handleAsync(chatMessages);
        
        // Add response message
        if (response.message) {
            this.messages.push(response.message);
            
            // If it's a stop message, we're done
            if (response.message instanceof StopMessage) {
                return;
            }
            
            // Check termination
            const stopMessage = await this.checkTerminationConditionAsync(this.messages);
            if (stopMessage) {
                this.messages.push(stopMessage);
                return;
            }
            
            // Continue to next agent
            await this.publishNextAsync();
        }
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
     * Creates a new RoundRobinGroupChat with specified agents and termination condition.
     * @param speakAgent The agent that speaks in the conversation
     * @param terminateAgent The agent that can terminate the conversation
     * @param terminationCondition Optional condition for chat termination
     * @returns A configured RoundRobinGroupChat instance
     */
    static create(
        speakAgent: IChatAgent,
        terminateAgent: IChatAgent,
        terminationCondition?: ITerminationCondition
    ): RoundRobinGroupChat {
        return new RoundRobinGroupChat(speakAgent, terminateAgent, terminationCondition);
    }
}
