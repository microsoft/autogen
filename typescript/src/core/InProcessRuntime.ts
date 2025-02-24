import { IAgentRuntime, AgentId, TopicId } from "../contracts/IAgentRuntime";
import { AgentType } from "../contracts/AgentType";
import { ISubscriptionDefinition } from "../contracts/ISubscriptionDefinition";
import { AgentProxy } from "../contracts/AgentProxy";
import { MessageDelivery, MessageEnvelope } from "./MessageDelivery";
import { IAgent } from "../contracts/IAgent";
import { MessageContext } from "../contracts/MessageContext";
import { UndeliverableException } from "../contracts/AgentExceptions";

/**
 * An in-process implementation of the agent runtime that manages message delivery and agent lifecycle.
 * This runtime executes all agents in the same process and provides synchronous message delivery.
 */
export class InProcessRuntime implements IAgentRuntime {
  /**
   * Gets or sets whether agents should receive their own messages.
   * When false, messages published by an agent will not be delivered to itself.
   */
  public deliverToSelf = false;
  private agentInstances = new Map<string, IAgent>();
  private subscriptions = new Map<string, ISubscriptionDefinition>();
  private agentFactories = new Map<string, (agentId: AgentId, runtime: IAgentRuntime) => Promise<IAgent>>();
  private messageDeliveryQueue: MessageDelivery[] = [];
  private isRunning = false;
  private messageProcessor?: ReturnType<typeof setInterval>;

  /**
   * Starts the runtime, initializing message processing.
   * @throws Error if the runtime is already running
   */
  async start(): Promise<void> {
    if (this.isRunning) {
      throw new Error("Runtime is already running");
    }
    this.isRunning = true;
    // Start continuous message processing
    this.messageProcessor = setInterval(() => {
      if (this.messageDeliveryQueue.length > 0) {
        this.processNextMessage();
      }
    }, 10);
  }

  /**
   * Stops the runtime, cleaning up resources and processing any remaining messages.
   */
  async stop(): Promise<void> {
    if (!this.isRunning) {
      return; // Change from throwing to just returning
    }
    
    if (this.messageProcessor) {
      clearInterval(this.messageProcessor);
      this.messageProcessor = undefined;
    }
    
    this.isRunning = false;

    // Process any remaining messages
    while (this.messageDeliveryQueue.length > 0) {
      await this.processNextMessage();
    }

    // Clear queue and subscriptions
    this.messageDeliveryQueue = [];
    this.subscriptions.clear();
  }

  /**
   * Internal service function for publishing messages.
   * @param envelope The message envelope to publish
   * @param deliveryToken Optional cancellation token
   */
  private async publishMessageServicer(envelope: MessageEnvelope, deliveryToken?: AbortSignal): Promise<void> {
    if (!envelope.topic) {
      throw new Error("Message must have a topic to be published.");
    }

    const topic = envelope.topic;
    const promises: Promise<void>[] = [];
    const sender = envelope.sender;
    
    console.log('Starting message delivery:', {
      topic,
      sender,
      subscriptionCount: this.subscriptions.size,
      deliverToSelf: this.deliverToSelf,
      isRunning: this.isRunning
    });

    for (const [id, subscription] of this.subscriptions.entries()) {
      if (subscription.matches(topic)) {
        const targetAgentId = subscription.mapToAgent(topic);
        
        // Determine whether this is a self-delivery attempt
        const isSelfDelivery = sender && 
            sender.type === targetAgentId.type && 
            sender.key === targetAgentId.key;

        console.log('Delivery check:', {
          subscriptionId: id,
          targetAgentId,
          isSelfDelivery,
          deliverToSelf: this.deliverToSelf,
          sender,
          shouldDeliver: sender === undefined || !isSelfDelivery || this.deliverToSelf
        });

        // Key fix: Deliver message if:
        // 1. There is no sender (external message) OR
        // 2. It's not a self-delivery scenario OR
        // 3. It is a self-delivery scenario AND deliverToSelf is true
        if (sender === undefined || !isSelfDelivery || (isSelfDelivery && this.deliverToSelf)) {
          const deliveryPromise = (async () => {
            try {
              const agent = await this.ensureAgentAsync(targetAgentId);
              console.log(`Delivering message to agent ${targetAgentId.type}/${targetAgentId.key}`, {
                messageType: typeof envelope.message,
                hasAgent: !!agent
              });

              const context = new MessageContext(envelope.messageId, envelope.cancellation);
              context.sender = sender;
              context.topic = topic;
              context.isRpc = false;
              await agent.onMessageAsync(envelope.message, context);
            } catch (error) {
              console.error(`Error during onMessageAsync:`, error);
            }
          })();

          promises.push(deliveryPromise);
        } else {
          console.log('Skipping self delivery');
        }
      }
    }

    await Promise.all(promises);
  }

  /**
   * Internal service function for sending direct messages.
   * @param envelope The message envelope to send
   * @param deliveryToken Optional cancellation token
   */
  private async sendMessageServicer(envelope: MessageEnvelope, deliveryToken?: AbortSignal): Promise<unknown> {
    if (!envelope.receiver) {
      throw new Error("Message must have a receiver to be sent.");
    }

    console.log('sendMessageServicer:', {
      receiver: envelope.receiver,
      message: envelope.message,
      isRpc: true
    });

    const context = new MessageContext(envelope.messageId, envelope.cancellation);
    context.sender = envelope.sender;
    context.isRpc = true;

    const agent = await this.ensureAgentAsync(envelope.receiver);
    console.log('Found agent for RPC:', {
      agentId: agent.id,
      agentType: agent.constructor.name
    });

    const response = await agent.onMessageAsync(envelope.message, context);
    console.log('RPC response:', { response });
    return response;
  }

  /**
   * Publishes a message to all subscribed agents.
   * @param message The message to publish
   * @param topic The topic to publish to
   * @param sender Optional sender information
   * @param messageId Optional message identifier
   * @param cancellation Optional cancellation token
   */
  async publishMessageAsync(
    message: unknown,
    topic: TopicId,
    sender?: AgentId,
    messageId?: string,
    cancellation?: AbortSignal
  ): Promise<void> {
    console.log('Publishing with:', { message, topic, sender });
    const delivery = new MessageEnvelope(message, messageId, cancellation)
      .withSender(sender)
      .forPublish(topic, (env, cancel) => this.publishMessageServicer(env, cancel));

    this.messageDeliveryQueue.push(delivery);
    await this.processNextMessage();
    // Wait for queue to process
    await new Promise(resolve => setTimeout(resolve, 100));
  }

  /**
   * Sends a message directly to a specific agent.
   * @param message The message to send
   * @param recipient The target agent
   * @param sender Optional sender information
   * @param messageId Optional message identifier
   * @param cancellation Optional cancellation token
   * @returns A promise that resolves with the agent's response
   */
  async sendMessageAsync(
    message: unknown,
    recipient: AgentId,
    sender?: AgentId,
    messageId?: string,
    cancellation?: AbortSignal
  ): Promise<unknown> {
    if (!this.isRunning) {
      throw new Error("Runtime not started");
    }

    console.log('Sending message:', { message, recipient, sender, isRunning: this.isRunning });
    
    const delivery = new MessageEnvelope(message, messageId, cancellation)
      .withSender(sender)
      .forSend(recipient, (env, cancel) => this.sendMessageServicer(env, cancel));

    this.messageDeliveryQueue.push(delivery);

    // Process the message immediately instead of waiting for timer
    await this.processNextMessage();

    // Wait for and return the result
    const result = await delivery.future;
    console.log('Send completed:', { result });
    return result;
  }

  /**
   * Gets metadata for an agent.
   * @param agentId The agent identifier
   * @returns The agent's metadata
   */
  async getAgentMetadataAsync(agentId: AgentId): Promise<unknown> {
    const agent = await this.ensureAgentAsync(agentId);
    return {
      type: agentId.type,
      key: agentId.key,
      description: (agent as any).description || ""
    };
  }

  /**
   * Adds a new subscription to the runtime.
   * @param subscription The subscription to add
   * @throws Error if a subscription with the same ID already exists
   */
  async addSubscriptionAsync(subscription: ISubscriptionDefinition): Promise<void> {
    if (this.subscriptions.has(subscription.id)) {
      throw new Error(`Subscription with id ${subscription.id} already exists.`);
    }
    this.subscriptions.set(subscription.id, subscription);
  }

  /**
   * Removes a subscription from the runtime.
   * @param subscriptionId The ID of the subscription to remove
   * @throws Error if the subscription doesn't exist
   */
  async removeSubscriptionAsync(subscriptionId: string): Promise<void> {
    if (!this.subscriptions.has(subscriptionId)) {
      throw new Error(`Subscription with id ${subscriptionId} does not exist.`);
    }
    this.subscriptions.delete(subscriptionId);
  }

  /**
   * Registers a factory function for creating agents of a specific type.
   * @param type The agent type to register
   * @param factoryFunc The factory function that creates agent instances
   * @returns The registered agent type
   * @throws Error if the agent type is already registered
   */
  async registerAgentFactoryAsync(
    type: AgentType,
    factoryFunc: (agentId: AgentId, runtime: IAgentRuntime) => Promise<IAgent>
  ): Promise<AgentType> {
    console.log('Registering agent factory:', { type, existingTypes: Array.from(this.agentFactories.keys()) });
    if (this.agentFactories.has(type)) {
      throw new Error(`Agent type ${type} already registered`);
    }
    this.agentFactories.set(type, factoryFunc);
    return type;
  }

  /**
   * Processes the next message in the delivery queue.
   * @param cancellation Optional cancellation token
   */
  private async processNextMessage(cancellation?: AbortSignal): Promise<void> {
    console.debug('Processing next message:', {
      queueLength: this.messageDeliveryQueue.length,
      isRunning: this.isRunning
    });

    if (!this.isRunning) {
      console.warn("Attempted to process message when runtime not running");
      return;
    }

    const delivery = this.messageDeliveryQueue.shift();
    if (delivery) {
      try {
        console.debug('Invoking delivery:', {
          messageType: delivery.message.message 
            ? typeof delivery.message.message === 'object' && delivery.message.message !== null
                ? delivery.message.message.constructor.name
                : typeof delivery.message.message
            : 'undefined',
          topic: delivery.message.topic,
          sender: delivery.message.sender
        });
        await delivery.invokeAsync(cancellation);
        // Add small delay to ensure message processing order
        await new Promise(resolve => setTimeout(resolve, 10));
      } catch (error) {
        console.error("Error processing message:", error);
        throw error; // Re-throw to ensure errors propagate
      }
    }
  }

  /**
   * Loads a state into a specific agent.
   * @param agentId The agent to load state into
   * @param state The state to load
   */
  async loadAgentStateAsync(agentId: AgentId, state: unknown): Promise<void> {
    const agent = await this.ensureAgentAsync(agentId);
    await agent.loadStateAsync(state);
  }

  /**
   * Saves the state of a specific agent.
   * @param agentId The agent whose state to save
   * @returns The saved state
   */
  async saveAgentStateAsync(agentId: AgentId): Promise<unknown> {
    const agent = await this.ensureAgentAsync(agentId);
    return await agent.saveStateAsync();
  }

  /**
   * Creates a proxy for interacting with an agent.
   * @param agentId The agent to create a proxy for
   * @returns A new agent proxy instance
   */
  async tryGetAgentProxyAsync(agentId: AgentId): Promise<AgentProxy> {
    return new AgentProxy(agentId, this);
  }

  /**
   * Gets or creates an agent instance.
   * @param agentId The agent identifier
   * @returns The agent instance
   * @throws UndeliverableException if the agent type is not registered
   */
  private async ensureAgentAsync(agentId: AgentId): Promise<IAgent> {
    const key = `${agentId.type}:${agentId.key}`;
    let agent = this.agentInstances.get(key);
    
    if (!agent) {
      const factory = this.agentFactories.get(agentId.type);
      if (!factory) {
        throw new UndeliverableException(`Agent type ${agentId.type} not found`);
      }
      agent = await factory(agentId, this);
      this.agentInstances.set(key, agent);
    }

    return agent;
  }
}