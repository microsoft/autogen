import {
  AgentMessageConfig,
  Message,
  TaskResult,
  RunStatus,
} from "../../../types/datamodel";

export interface ThreadState {
  messages: AgentMessageConfig[];
  finalResult?: any;
  status: RunStatus;
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

// Create timeout configuration based on user settings
export const createTimeoutConfig = (timeoutMinutes: number = 3) => ({
  DURATION_MS: timeoutMinutes * 60 * 1000, // timeout in milliseconds
  DURATION_SEC: timeoutMinutes * 60, // timeout in seconds
  WEBSOCKET_CODE: 4000, // WebSocket close code for timeout
  DEFAULT_MESSAGE: `Input timeout after ${timeoutMinutes} minute${timeoutMinutes !== 1 ? 's' : ''}`,
  WARNING_THRESHOLD_SEC: 30, // Show warning when 30 seconds remaining
});

// Default timeout config for backward compatibility
export const TIMEOUT_CONFIG = createTimeoutConfig(3);

export interface TimeoutError {
  code: typeof TIMEOUT_CONFIG.WEBSOCKET_CODE;
  message: string;
}
