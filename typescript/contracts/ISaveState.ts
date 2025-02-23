export interface ISaveState {
  saveStateAsync(): Promise<unknown>;
  loadStateAsync(state: unknown): Promise<void>;
  // Interface for saving/loading agent state
}