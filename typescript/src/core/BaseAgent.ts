import { IAgentRuntime, AgentId } from "../contracts/IAgentRuntime";
import { IAgent } from "../contracts/IAgent";
import { MessageContext } from "../contracts/MessageContext";
import { IHandle } from "../contracts/IHandle";

export abstract class BaseAgent implements IAgent, IHandle<unknown> {
  public readonly id: AgentId;
  protected runtime: IAgentRuntime;
  protected description: string;

  constructor(id: AgentId, runtime: IAgentRuntime, description: string) {
    this.id = id;
    this.runtime = runtime;
    this.description = description;
  }

  get metadata() {
    return {
      type: this.id.type,
      key: this.id.key,
      description: this.description
    };
  }

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

  abstract handleAsync(message: unknown, context: MessageContext): Promise<unknown>;

  async saveStateAsync(): Promise<unknown> {
    return {};
  }

  async loadStateAsync(state: unknown): Promise<void> {}
}