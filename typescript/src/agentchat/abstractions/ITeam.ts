import { TaskFrame } from "./Tasks";

/**
 * Defines a team of agents that can work together to accomplish tasks.
 */
export interface ITeam {
    /**
     * Gets a unique identifier for this team.
     */
    readonly teamId: string;

    /**
     * Executes a task and returns a stream of frames containing intermediate messages and final results.
     * @param task The task to execute, typically a string or message
     * @param cancellation Optional cancellation token
     * @returns An async iterable of task frames containing messages or results
     */
    streamAsync(task: string | unknown, cancellation?: AbortSignal): AsyncIterable<TaskFrame>;

    /**
     * Resets the team to its initial state.
     * @param cancellation Optional cancellation token
     */
    resetAsync(cancellation?: AbortSignal): Promise<void>;
}
