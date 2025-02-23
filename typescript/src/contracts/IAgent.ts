import { AgentId } from "./IAgentRuntime";

export interface IAgent {
  readonly id: AgentId;
  onMessageAsync(message: unknown, context: unknown): Promise<unknown>;
  saveStateAsync(): Promise<unknown>;
  loadStateAsync(state: unknown): Promise<void>;
}