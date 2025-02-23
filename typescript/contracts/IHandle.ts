import { MessageContext } from "./MessageContext";

// Generic interface for message handlers
export interface IHandle<TMessage> {
  handleAsync(message: TMessage, context: MessageContext): Promise<unknown>;
}