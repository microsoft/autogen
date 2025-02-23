export class ResultSink<T> {
  private resolve?: (value: T) => void;
  private reject?: (error: Error) => void;
  
  readonly future: Promise<T>;

  constructor() {
    this.future = new Promise<T>((resolve, reject) => {
      this.resolve = resolve;
      this.reject = reject;
    });
  }

  setResult(result: T): void {
    this.resolve?.(result);
  }

  setError(error: Error): void {
    this.reject?.(error);
  }
}
