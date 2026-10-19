/**
 * Defines a contract for saving and loading the state of an object.
 * The state must be JSON serializable.
 */
export interface ISaveState {
  /**
   * Saves the current state of the object.
   * @returns A promise that resolves to the saved state. The structure of the state 
   * is implementation-defined but must be JSON serializable.
   */
  saveStateAsync(): Promise<unknown>;

  /**
   * Loads a previously saved state into the object.
   * @param state A state object representing the saved state. The structure of the state
   * is implementation-defined but must be JSON serializable.
   * @returns A promise that completes when the state has been loaded.
   */
  loadStateAsync(state: unknown): Promise<void>;
}