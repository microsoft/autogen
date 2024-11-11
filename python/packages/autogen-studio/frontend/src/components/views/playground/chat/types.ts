import { Message, TaskResult } from "../../../types/datamodel";

export type ThreadStatus = "streaming" | "complete" | "error" | "cancelled";

export interface ThreadState {
  messages: any[];
  finalResult?: any;
  status: ThreadStatus;
  isExpanded: boolean;
}

export interface ThreadState {
  messages: any[];
  finalResult?: any;
  status: "streaming" | "complete" | "error" | "cancelled";
  isExpanded: boolean;
  reason?: string;
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

export interface SocketMessage {
  type: "message" | "result" | "completion";
  data?: {
    source?: string;
    models_usage?: ModelUsage | null;
    content?: string;
    task_result?: TaskResult;
  };
  status?: ThreadStatus;
  timestamp?: string;
  error?: string;
}
