import { AgentType } from "./AgentType";
import { IAgent } from "./IAgent";
import { ISubscriptionDefinition } from "./ISubscriptionDefinition";

/**
 * Represents a unique identifier for an agent instance.
 */
export interface AgentId {
  /** The type of agent */
  type: string;
  /** Unique key identifying this agent instance */
  key: string;
}

/**
 * Represents a topic identifier for message routing.
 */
export interface TopicId {
  /** The type of topic */
  type: string;
  /** The source of the topic */
  source: string;
}

/**
 * Defines the runtime environment for agents, managing message sending, subscriptions, 
 * agent resolution, and state persistence.
 */
export interface IAgentRuntime {
  /**
   * Publishes a message to all agents subscribed to the given topic.
   * No responses are expected from publishing.
   * @param message The message to publish
   * @param topic The topic to publish the message to
   * @param sender The agent sending the message
   * @param messageId A unique message ID. If null, a new one will be generated
   * @throws {UndeliverableException} If the message cannot be delivered
   */
  publishMessageAsync(
    message: unknown,
    topic: TopicId,
    sender?: AgentId,
    messageId?: string
  ): Promise<void>;

  /**
   * Sends a message to an agent and gets a response.
   * @param message The message to send
   * @param recipient The agent to send the message to
   * @param sender The agent sending the message
   * @param messageId A unique message ID. If null, a new one will be generated
   * @returns A promise resolving to the response from the agent
   * @throws {UndeliverableException} If the message cannot be delivered
   * @throws {CantHandleException} If the recipient cannot handle the message
   */
  sendMessageAsync(
    message: unknown,
    recipient: AgentId,
    sender?: AgentId,
    messageId?: string
  ): Promise<unknown>;

  /**
   * Retrieves metadata for an agent.
   * @param agentId The ID of the agent
   * @returns A promise resolving to the agent's metadata
   */
  getAgentMetadataAsync(agentId: AgentId): Promise<unknown>;

  /**
   * Loads a previously saved state into an agent.
   * @param agentId The ID of the agent whose state is being restored
   * @param state The state to restore
   */
  loadAgentStateAsync(agentId: AgentId, state: unknown): Promise<void>;

  /**
   * Saves the state of an agent.
   * @param agentId The ID of the agent whose state is being saved
   * @returns A promise resolving to the saved state
   */
  saveAgentStateAsync(agentId: AgentId): Promise<unknown>;

  /**
   * Registers an agent factory with the runtime.
   * @param type The agent type to associate with the factory
   * @param factoryFunc A function that creates the agent instance
   * @returns The registered agent type
   */
  registerAgentFactoryAsync(
    type: AgentType,
    factoryFunc: (agentId: AgentId, runtime: IAgentRuntime) => Promise<IAgent>
  ): Promise<AgentType>;

  /**
   * Adds a new subscription for the runtime to handle when processing published messages.
   * @param subscription The subscription to add
   */
  addSubscriptionAsync(subscription: ISubscriptionDefinition): Promise<void>;

  /**
   * Removes a subscription from the runtime.
   * @param subscriptionId The unique identifier of the subscription to remove
   * @throws {Error} If the subscription does not exist
   */
  removeSubscriptionAsync(subscriptionId: string): Promise<void>;

  /**
   * Starts the agent runtime, initializing all necessary resources and services.
   * Must be called before any other operations can be performed.
   * @returns A promise that resolves when the runtime has started successfully
   * @throws {Error} If the runtime fails to start or is already running
   */
  start(): Promise<void>;

  /**
   * Stops the agent runtime, cleaning up resources and shutting down services.
   * No further operations should be performed after stopping the runtime.
   * @returns A promise that resolves when the runtime has stopped successfully
   * @throws {Error} If the runtime fails to stop or is not running
   */
  stop(): Promise<void>;
}