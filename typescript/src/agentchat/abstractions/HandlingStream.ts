/**
 * Interface for streaming handlers that can process an input type and produce an output type.
 */
export interface IHandleStream<TIn, TOut> {
    /**
     * Processes the input and produces a stream of output.
     * @param input The input to process
     * @param cancellation Optional token to cancel the operation
     * @returns An async iterable of output items
     */
    streamAsync(input: TIn, cancellation?: AbortSignal): AsyncIterable<TOut>;
}
