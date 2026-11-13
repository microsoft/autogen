import { MessageContext } from "../contracts/MessageContext";
import { IHandle } from "../contracts/IHandle";

/**
 * A class that manages the invocation of message handlers.
 */
export class HandlerInvoker {
  /**
   * Creates a new handler invoker.
   * @param handler The handler that will process messages
   */
  constructor(private handler: IHandle<unknown>) {}

  /**
   * Invokes the handler with the given message and context.
   * @param message The message to handle
   * @param context The context for message handling
   * @returns A promise that resolves to the handler's response
   */
  async invoke(message: unknown, context: MessageContext): Promise<unknown> {
    return await this.handler.handleAsync(message, context);
  }

  /**
   * Gets an invoker for a specific message type on a target object.
   * @param target The object that contains handler methods
   * @param messageType The type of message to handle
   * @returns A promise that resolves to a handler invoker if found, undefined otherwise
   */
  static async getInvokerForType(target: object, messageType: string): Promise<HandlerInvoker | undefined> {
    // Implementation for finding handler method on target that matches messageType
    // This would use reflection/type information to find appropriate handler
    return undefined;
  }
}
