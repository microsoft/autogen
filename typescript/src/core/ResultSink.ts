/**
 * A generic class that acts as a promise-like container for asynchronous results.
 * @template T The type of result that will be stored in the sink
 */
export class ResultSink<T> {
  private resolve?: (value: T) => void;
  private reject?: (error: Error) => void;
  
  /**
   * Gets the promise that will resolve with the result.
   */
  readonly future: Promise<T>;

  /**
   * Creates a new instance of ResultSink.
   */
  constructor() {
    this.future = new Promise<T>((resolve, reject) => {
      this.resolve = resolve;
      this.reject = reject;
    });
  }

  /**
   * Sets the successful result value, resolving the future.
   * @param result The result value to set
   */
  setResult(result: T): void {
    this.resolve?.(result);
  }

  /**
   * Sets an error, rejecting the future.
   * @param error The error that occurred
   */
  setError(error: Error): void {
    this.reject?.(error);
  }
}
