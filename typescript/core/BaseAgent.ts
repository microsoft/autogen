import { IAgentRuntime, AgentId } from "../contracts/IAgentRuntime";
import { IAgent } from "../contracts/IAgent";

export abstract class BaseAgent implements IAgent {
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

  async onMessageAsync(message: unknown, context: unknown): Promise<unknown> {
    return null;
  }

  async saveStateAsync(): Promise<unknown> {
    return {};
  }

  async loadStateAsync(state: unknown): Promise<void> {}
}