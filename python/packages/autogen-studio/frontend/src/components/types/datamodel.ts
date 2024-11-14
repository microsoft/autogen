export interface RequestUsage {
  prompt_tokens: number;
  completion_tokens: number;
}

export interface ImageContent {
  url: string;
  alt?: string;
}

export interface FunctionCall {
  id: string;
  arguments: string; // JSON string
  name: string;
}

export interface FunctionExecutionResult {
  call_id: string;
  content: string;
}

// Base message configuration (maps to Python BaseMessage)
export interface BaseMessageConfig {
  source: string;
  models_usage?: RequestUsage;
}

// Message configurations (mapping directly to Python classes)
export interface TextMessageConfig extends BaseMessageConfig {
  content: string;
}

export interface MultiModalMessageConfig extends BaseMessageConfig {
  content: (string | ImageContent)[];
}

export interface StopMessageConfig extends BaseMessageConfig {
  content: string;
}

export interface HandoffMessageConfig extends BaseMessageConfig {
  content: string;
  target: string;
}

export interface ToolCallMessageConfig extends BaseMessageConfig {
  content: FunctionCall[];
}

export interface ToolCallResultMessageConfig extends BaseMessageConfig {
  content: FunctionExecutionResult[];
}

// Message type unions (matching Python type aliases)
export type InnerMessageConfig =
  | ToolCallMessageConfig
  | ToolCallResultMessageConfig;

export type ChatMessageConfig =
  | TextMessageConfig
  | MultiModalMessageConfig
  | StopMessageConfig
  | HandoffMessageConfig;

export type AgentMessageConfig =
  | TextMessageConfig
  | MultiModalMessageConfig
  | StopMessageConfig
  | HandoffMessageConfig
  | ToolCallMessageConfig
  | ToolCallResultMessageConfig;

// Database model
export interface DBModel {
  id?: number;
  user_id?: string;
  created_at?: string;
  updated_at?: string;
}

export interface Message extends DBModel {
  config: AgentMessageConfig;
  session_id: number;
  run_id: string;
}

export interface Session extends DBModel {
  name: string;
  team_id?: number;
}

// WebSocket message types
export type ThreadStatus = "streaming" | "complete" | "error" | "cancelled";

export interface WebSocketMessage {
  type: "message" | "result" | "completion";
  data: {
    source: string;
    models_usage?: RequestUsage;
    content: unknown;
    task_result?: TaskResult;
  };
  status?: ThreadStatus;
  error?: string;
}

export interface TaskResult {
  messages: AgentMessageConfig[];
  usage: string;
  duration: number;
  stop_reason?: string;
}

export type ModelTypes = "OpenAIChatCompletionClient";

export type AgentTypes = "AssistantAgent" | "CodingAssistantAgent";

export type TeamTypes = "RoundRobinGroupChat" | "SelectorGroupChat";

export type TerminationTypes =
  | "MaxMessageTermination"
  | "StopMessageTermination"
  | "TextMentionTermination";

export interface ModelConfig {
  model: string;
  model_type: ModelTypes;
  api_key?: string;
  base_url?: string;
}

export interface ToolConfig {
  name: string;
  description: string;
  content: string;
}
export interface AgentConfig {
  name: string;
  agent_type: AgentTypes;
  system_message?: string;
  model_client?: ModelConfig;
  tools?: ToolConfig[];
  description?: string;
}
export interface TerminationConfig {
  termination_type: TerminationTypes;
  max_messages?: number;
  text?: string;
}

export interface TeamConfig {
  name: string;
  participants: AgentConfig[];
  team_type: TeamTypes;
  model_client?: ModelConfig;
  termination_condition?: TerminationConfig;
  selector_config?: string;
}

export interface Team extends DBModel {
  config: TeamConfig;
}
