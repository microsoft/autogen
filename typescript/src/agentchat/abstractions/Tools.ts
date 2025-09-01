import { ChatMessage } from "./Messages";

/**
 * Represents a tool that can be used by an agent to perform specific tasks.
 */
export interface ITool {
    /**
     * Gets the name of the tool.
     */
    readonly name: string;

    /**
     * Gets the description of what the tool does and how to use it.
     */
    readonly description: string;

    /**
     * Executes the tool with the given parameters.
     * @param parameters The parameters to pass to the tool
     * @returns A ChatMessage containing the result of the tool execution
     */
    executeAsync(parameters: Record<string, unknown>): Promise<ChatMessage>;
}

/**
 * Represents the result of a tool execution.
 */
export interface ToolResult {
    /**
     * Gets whether the tool execution was successful.
     */
    success: boolean;

    /**
     * Gets the message describing the result or error.
     */
    message: string;

    /**
     * Gets any additional data produced by the tool.
     */
    data?: unknown;
}
