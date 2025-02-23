import { MessageContext } from "../contracts/MessageContext";
import { IHandle } from "../contracts/IHandle";

export class HandlerInvoker {
  constructor(private handler: IHandle<unknown>) {}

  async invoke(message: unknown, context: MessageContext): Promise<unknown> {
    return await this.handler.handleAsync(message, context);
  }

  static async getInvokerForType(target: object, messageType: string): Promise<HandlerInvoker | undefined> {
    // Implementation for finding handler method on target that matches messageType
    // This would use reflection/type information to find appropriate handler
    return undefined;
  }
}
