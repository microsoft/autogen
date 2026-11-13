import { IAgentRuntime, AgentId } from "./IAgentRuntime";

/**
 * A helper class that allows you to use an AgentId in place of its associated IAgent.
 */
export class AgentProxy {
  /**
   * Gets the target agent for this proxy.
   */
  public readonly agentId: AgentId;

  /**
   * The runtime instance used to interact with agents.
   */
  private runtime: IAgentRuntime;

  /**
   * Creates a new instance of the AgentProxy class.
   * @param agentId The ID of the agent to proxy
   * @param runtime The runtime instance to use for agent interactions
   */
  constructor(agentId: AgentId, runtime: IAgentRuntime) {
    this.agentId = agentId;
    this.runtime = runtime;
  }

  /**
   * Gets the metadata of the agent.
   * @returns A promise that resolves to the agent's metadata
   */
  async getMetadata(): Promise<unknown> {
    return this.runtime.getAgentMetadataAsync(this.agentId);
  }

  /**
   * Sends a message to the agent and processes the response.
   * @param message The message to send to the agent
   * @param sender The agent that is sending the message
   * @param messageId The message ID. If null, a new message ID will be generated
   * @returns A promise resolving to the response from the agent
   */
  async sendMessageAsync(
    message: unknown,
    sender?: AgentId,
    messageId?: string
  ): Promise<unknown> {
    return this.runtime.sendMessageAsync(message, this.agentId, sender, messageId);
  }

  /**
   * Loads the saved state into the agent.
   * @param state A dictionary representing the state of the agent
   */
  async loadStateAsync(state: unknown): Promise<void> {
    return this.runtime.loadAgentStateAsync(this.agentId, state);
  }

  /**
   * Saves the state of the agent.
   * @returns A promise resolving to a dictionary containing the saved state
   */
  async saveStateAsync(): Promise<unknown> {
    return this.runtime.saveAgentStateAsync(this.agentId);
  }
}