import { AgentId, TopicId } from "./IAgentRuntime";

// Represents the context of a message in the runtime
export interface MessageContext {
  messageId: string;
  sender?: AgentId;
  topic?: TopicId;
  isRpc?: boolean;
  // ...existing code...
}
