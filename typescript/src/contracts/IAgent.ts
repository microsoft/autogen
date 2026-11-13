import { AgentId } from "./IAgentRuntime";

/**
 * Represents an agent within the runtime that can process messages, maintain state, 
 * and be closed when no longer needed.
 */
export interface IAgent {
  /**
   * Gets the unique identifier of the agent.
   */
  readonly id: AgentId;

  /**
   * Handles an incoming message for the agent.
   * This should only be called by the runtime, not by other agents.
   * @param message The received message. The type should match one of the expected subscription types.
   * @param context The context of the message, providing additional metadata.
   * @returns A promise resolving to a response to the message. Can be null if no reply is necessary.
   * @throws {CantHandleException} If the agent cannot handle the message.
   * @throws {OperationCanceledException} If the message was cancelled.
   */
  onMessageAsync(message: unknown, context: unknown): Promise<unknown>;

  /**
   * Saves the state of the agent. The result must be JSON serializable.
   * @returns A promise resolving to a dictionary containing the saved state.
   */
  saveStateAsync(): Promise<unknown>;

  /**
   * Loads the saved state into the agent.
   * @param state The state to restore.
   * @returns A promise that completes when the state has been loaded.
   */
  loadStateAsync(state: unknown): Promise<void>;
}