import { MessageContext } from "./MessageContext";

/**
 * Defines a handler interface for processing items of type TMessage.
 * @template TMessage The type of message to be handled.
 */
export interface IHandle<TMessage> {
  /**
   * Handles the specified message asynchronously.
   * @param message The message to be handled.
   * @param context The context information for the message being handled.
   * @returns A promise that resolves to the result of handling the message.
   */
  handleAsync(message: TMessage, context: MessageContext): Promise<unknown>;
}