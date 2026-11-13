/**
 * Represents metadata associated with an agent, including its type, unique key, and description.
 */
export interface AgentMetadata {
  /**
   * An identifier that associates an agent with a specific factory function.
   * Strings may only be composed of alphanumeric letters (a-z, 0-9), or underscores (_).
   */
  type: string;

  /**
   * A unique key identifying the agent instance.
   * Strings may only be composed of alphanumeric letters (a-z, 0-9), or underscores (_).
   */
  key: string;

  /**
   * A brief description of the agent's purpose or functionality.
   */
  description?: string;
}