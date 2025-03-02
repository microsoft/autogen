import { IAgentRuntime, AgentId } from "../contracts/IAgentRuntime";
import { IAgent } from "../contracts/IAgent";
import { MessageContext } from "../contracts/MessageContext";
import { IHandle } from "../contracts/IHandle";

/**
 * Represents the base class for an agent in the AutoGen system.
 * Provides common functionality for message handling and state management.
 */
export abstract class BaseAgent implements IAgent, IHandle<unknown> {
  /**
   * Gets the unique identifier of the agent.
   */
  public readonly id: AgentId;

  /**
   * The runtime instance used to interact with other agents.
   */
  protected runtime: IAgentRuntime;

  /**
   * A brief description of the agent's purpose or functionality.
   */
  protected description: string;

  /**
   * Creates a new instance of the BaseAgent class.
   * @param id The unique identifier for this agent
   * @param runtime The runtime instance this agent will use
   * @param description A brief description of the agent's purpose
   */
  constructor(id: AgentId, runtime: IAgentRuntime, description: string) {
    this.id = id;
    this.runtime = runtime;
    this.description = description;
  }

  /**
   * Gets metadata associated with the agent.
   */
  get metadata() {
    return {
      type: this.id.type,
      key: this.id.key,
      description: this.description
    };
  }

  /**
   * Handles an incoming message for the agent.
   * This implementation logs the message and delegates to handleAsync.
   * @param message The received message
   * @param context The context of the message
   * @returns A promise resolving to the response
   */
  async onMessageAsync(message: unknown, context: MessageContext): Promise<unknown> {
    console.log(`BaseAgent.onMessageAsync:`, { 
      agentId: this.id,
      message,
      context,
      handlerType: this.constructor.name
    });

    try {
      const result = await this.handleAsync(message, context);
      console.log(`BaseAgent.onMessageAsync - handleAsync completed`, { result });
      return result;
    } catch (error) {
      console.error(`BaseAgent.onMessageAsync - handleAsync failed`, error);
      throw error;
    }
  }

  /**
   * Abstract method that must be implemented by derived classes to handle messages.
   * @param message The message to handle
   * @param context The context for message handling
   * @returns A promise resolving to the handler's response
   */
  abstract handleAsync(message: unknown, context: MessageContext): Promise<unknown>;

  /**
   * Saves the current state of the agent.
   * Base implementation returns an empty object.
   * @returns A promise resolving to the saved state
   */
  async saveStateAsync(): Promise<unknown> {
    return {};
  }

  /**
   * Loads a previously saved state into the agent.
   * Base implementation does nothing.
   * @param state The state to restore
   */
  async loadStateAsync(state: unknown): Promise<void> {}
}