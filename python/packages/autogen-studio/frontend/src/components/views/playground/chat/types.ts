import {
  AgentMessageConfig,
  Message,
  TaskResult,
  ThreadStatus,
} from "../../../types/datamodel";

export interface ThreadState {
  messages: AgentMessageConfig[];
  finalResult?: any;
  status: ThreadStatus;
  isExpanded: boolean;
  reason?: string;
  inputRequest?: {
    prompt: string;
    isPending: boolean;
  };
}
export interface MessageListProps {
  messages: Message[];
  threadMessages: Record<string, ThreadState>;
  setThreadMessages: React.Dispatch<
    React.SetStateAction<Record<string, ThreadState>>
  >; // Add this
  onRetry: (query: string) => void;
  onCancel: (runId: string) => void;
  loading: boolean;
}

export interface ModelUsage {
  prompt_tokens: number;
  completion_tokens: number;
}
