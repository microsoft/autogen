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

export const TIMEOUT_CONFIG = {
  DURATION_MS: 3 * 60 * 1000, // 3 minutes in milliseconds
  DURATION_SEC: 3 * 60, // 3 minutes in seconds
  WEBSOCKET_CODE: 4000, // WebSocket close code for timeout
  DEFAULT_MESSAGE: "Input timeout after 3 minutes",
  WARNING_THRESHOLD_SEC: 30, // Show warning when 30 seconds remaining
} as const;

export interface TimeoutError {
  code: typeof TIMEOUT_CONFIG.WEBSOCKET_CODE;
  message: string;
}
