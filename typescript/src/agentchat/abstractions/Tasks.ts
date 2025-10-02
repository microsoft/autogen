import { AgentMessage } from "./Messages";

/**
 * Represents a frame of task execution, containing either a message or result.
 */
export class TaskFrame {
    public readonly isResult: boolean;
    public readonly message?: AgentMessage;
    public readonly result?: TaskResult;

    /**
     * Creates a new task frame.
     * @param messageOrResult Either an AgentMessage or TaskResult
     */
    constructor(messageOrResult: AgentMessage | TaskResult) {
        if (messageOrResult instanceof TaskResult) {
            this.isResult = true;
            this.result = messageOrResult;
        } else {
            this.isResult = false;
            this.message = messageOrResult;
        }
    }
}

/**
 * Represents the result of a task execution, including all messages generated.
 */
export class TaskResult {
    /**
     * Gets the messages generated during task execution.
     */
    public readonly messages: AgentMessage[];

    /**
     * Creates a new task result.
     * @param messages The messages generated during task execution
     */
    constructor(messages: AgentMessage[]) {
        this.messages = messages;
    }
}
