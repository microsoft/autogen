import { ITeam } from "../abstractions/ITeam";
import { TaskFrame, TaskResult } from "../abstractions/Tasks";
import { AgentMessage, ChatMessage } from "../abstractions/Messages";
import { ITerminationCondition } from "../abstractions/Termination";
import { GroupChatOptions } from "./GroupChatOptions";
import { GroupChatManagerBase } from "./GroupChatManagerBase";
import { GroupChatStart, GroupChatRequestPublish } from "./Events";
import { MessageContext } from "../../contracts/MessageContext";

/**
 * Base class for implementing group chat functionality.
 */
export abstract class GroupChatBase extends GroupChatManagerBase implements ITeam {
    /**
     * Gets a unique identifier for this team.
     */
    public teamId: string;

    /**
     * Creates a new instance of GroupChatBase.
     * @param options Configuration options for the group chat
     */
    constructor(options: GroupChatOptions) {
        super(options);
        this.teamId = crypto.randomUUID();
    }

    /**
     * Executes a task and returns a stream of frames containing intermediate messages and final results.
     * @param task The task to execute, typically a string or message
     * @param cancellation Optional cancellation token
     */
    async *streamAsync(task: string | unknown, cancellation?: AbortSignal): AsyncIterableIterator<TaskFrame> {
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

        // Convert messages to frames and yield
        yield new TaskFrame(new TaskResult(this.messages));
    }

    /**
     * Creates a new GroupChatBase with specified options.
     * @param groupChatTopicType Topic type for group chat messages
     * @param outputTopicType Topic type for output messages
     * @param terminationCondition Optional condition for chat termination
     * @param maxTurns Optional maximum number of turns
     */
    protected static createBase<T extends GroupChatBase>(
        this: new (options: GroupChatOptions) => T,
        groupChatTopicType: string,
        outputTopicType: string,
        terminationCondition?: ITerminationCondition,
        maxTurns?: number
    ): T {
        const options = new GroupChatOptions(groupChatTopicType, outputTopicType);
        options.terminationCondition = terminationCondition;
        options.maxTurns = maxTurns;
        return new this(options);
    }

    /**
     * Reset the team to its initial state.
     * @param cancellation Optional cancellation token
     */
    async resetAsync(cancellation?: AbortSignal): Promise<void> {
        await super.resetAsync();
    }
}
