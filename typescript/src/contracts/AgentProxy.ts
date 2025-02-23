import { IAgentRuntime, AgentId } from "./IAgentRuntime";

export class AgentProxy {
  public readonly agentId: AgentId;
  private runtime: IAgentRuntime;

  constructor(agentId: AgentId, runtime: IAgentRuntime) {
    this.agentId = agentId;
    this.runtime = runtime;
  }

  async getMetadata(): Promise<unknown> {
    return this.runtime.getAgentMetadataAsync(this.agentId);
  }

  async sendMessageAsync(
    message: unknown,
    sender?: AgentId,
    messageId?: string
  ): Promise<unknown> {
    return this.runtime.sendMessageAsync(message, this.agentId, sender, messageId);
  }

  async loadStateAsync(state: unknown): Promise<void> {
    return this.runtime.loadAgentStateAsync(this.agentId, state);
  }

  async saveStateAsync(): Promise<unknown> {
    return this.runtime.saveAgentStateAsync(this.agentId);
  }
}