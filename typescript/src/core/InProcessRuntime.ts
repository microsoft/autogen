import { IAgentRuntime, AgentId, TopicId } from "../contracts/IAgentRuntime";
import { AgentType } from "../contracts/AgentType";
import { ISubscriptionDefinition } from "../contracts/ISubscriptionDefinition";
import { AgentProxy } from "../contracts/AgentProxy";
import { MessageDelivery, MessageEnvelope } from "./MessageDelivery";
import { IAgent } from "../contracts/IAgent";
import { MessageContext } from "../contracts/MessageContext";
import { UndeliverableException } from "../contracts/AgentExceptions";

export class InProcessRuntime implements IAgentRuntime {
  public deliverToSelf = false;
  private agentInstances = new Map<string, IAgent>();
  private subscriptions = new Map<string, ISubscriptionDefinition>();
  private agentFactories = new Map<string, (agentId: AgentId, runtime: IAgentRuntime) => Promise<IAgent>>();
  private messageDeliveryQueue: MessageDelivery[] = [];
  private isRunning = false;

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
      deliverToSelf: this.deliverToSelf
    });

    for (const [id, subscription] of this.subscriptions.entries()) {
      if (subscription.matches(topic)) {
        const targetAgentId = subscription.mapToAgent(topic);
        
        // Check if this is a self-delivery scenario
        const isSelfDelivery = sender && 
            sender.type === targetAgentId.type && 
            sender.key === targetAgentId.key;

        console.log('Delivery check:', {
          subscriptionId: id,
          targetAgentId,
          isSelfDelivery,
          deliverToSelf: this.deliverToSelf,
          sender
        });
            
        // Fix: Only deliver if either:
        // 1. It's not a self-delivery case (sender undefined or different from target) OR
        // 2. deliverToSelf is true and it is a self-delivery case
        if (!isSelfDelivery || (isSelfDelivery && this.deliverToSelf)) {
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

  private async sendMessageServicer(envelope: MessageEnvelope, deliveryToken?: AbortSignal): Promise<unknown> {
    if (!envelope.receiver) {
      throw new Error("Message must have a receiver to be sent.");
    }

    const context = new MessageContext(envelope.messageId, envelope.cancellation);
    context.sender = envelope.sender;
    context.isRpc = false;

    const agent = await this.ensureAgentAsync(envelope.receiver);
    return await agent.onMessageAsync(envelope.message, context);
  }

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

  async sendMessageAsync(
    message: unknown,
    recipient: AgentId,
    sender?: AgentId,
    messageId?: string,
    cancellation?: AbortSignal
  ): Promise<unknown> {
    const delivery = new MessageEnvelope(message, messageId, cancellation)
      .withSender(sender)
      .forSend(recipient, (env, cancel) => this.sendMessageServicer(env, cancel));

    this.messageDeliveryQueue.push(delivery);
    return delivery.future;
  }

  async getAgentMetadataAsync(agentId: AgentId): Promise<unknown> {
    const agent = await this.ensureAgentAsync(agentId);
    return {
      type: agentId.type,
      key: agentId.key,
      description: (agent as any).description || ""
    };
  }

  async addSubscriptionAsync(subscription: ISubscriptionDefinition): Promise<void> {
    if (this.subscriptions.has(subscription.id)) {
      throw new Error(`Subscription with id ${subscription.id} already exists.`);
    }
    this.subscriptions.set(subscription.id, subscription);
  }

  async removeSubscriptionAsync(subscriptionId: string): Promise<void> {
    if (!this.subscriptions.has(subscriptionId)) {
      throw new Error(`Subscription with id ${subscriptionId} does not exist.`);
    }
    this.subscriptions.delete(subscriptionId);
  }

  async registerAgentFactoryAsync(
    type: AgentType,
    factoryFunc: (agentId: AgentId, runtime: IAgentRuntime) => Promise<IAgent>
  ): Promise<AgentType> {
    if (this.agentFactories.has(type)) {
      throw new Error(`Agent type ${type} already registered`);
    }
    this.agentFactories.set(type, factoryFunc);
    return type;
  }

  private async processNextMessage(cancellation?: AbortSignal): Promise<void> {
    const delivery = this.messageDeliveryQueue.shift();
    if (delivery) {
      await delivery.invokeAsync(cancellation);
    }
  }

  async loadAgentStateAsync(agentId: AgentId, state: unknown): Promise<void> {
    const agent = await this.ensureAgentAsync(agentId);
    await agent.loadStateAsync(state);
  }

  async saveAgentStateAsync(agentId: AgentId): Promise<unknown> {
    const agent = await this.ensureAgentAsync(agentId);
    return await agent.saveStateAsync();
  }

  async tryGetAgentProxyAsync(agentId: AgentId): Promise<AgentProxy> {
    return new AgentProxy(agentId, this);
  }
}