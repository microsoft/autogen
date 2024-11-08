import { Message, TaskResult } from "../../../types/datamodel";

export interface ThreadState {
  messages: any[];
  finalResult?: any;
  status: "streaming" | "complete" | "error" | "cancelled";
  isExpanded: boolean;
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
  status?: string;
  timestamp?: string;
}
