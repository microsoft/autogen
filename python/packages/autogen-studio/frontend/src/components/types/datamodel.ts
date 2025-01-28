export interface RequestUsage {
  prompt_tokens: number;
  completion_tokens: number;
}

export interface ImageContent {
  url: string;
  alt?: string;
  data?: string;
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
  version?: number;
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

export interface SessionRuns {
  runs: Run[];
}

export interface BaseConfig {
  component_type: string;
  version?: string;
  description?: string;
}

export interface WebSocketMessage {
  type: "message" | "result" | "completion" | "input_request" | "error";
  data?: AgentMessageConfig | TaskResult;
  status?: RunStatus;
  error?: string;
  timestamp?: string;
}

export interface TaskResult {
  messages: AgentMessageConfig[];
  stop_reason?: string;
}

export type ModelTypes =
  | "OpenAIChatCompletionClient"
  | "AzureOpenAIChatCompletionClient";

export type AgentTypes =
  | "AssistantAgent"
  | "UserProxyAgent"
  | "MultimodalWebSurfer"
  | "FileSurfer"
  | "MagenticOneCoderAgent";

export type ToolTypes = "PythonFunction";

export type TeamTypes =
  | "RoundRobinGroupChat"
  | "SelectorGroupChat"
  | "MagenticOneGroupChat";

export type TerminationTypes =
  | "MaxMessageTermination"
  | "StopMessageTermination"
  | "TextMentionTermination"
  | "TimeoutTermination"
  | "CombinationTermination";

export type ComponentTypes =
  | "team"
  | "agent"
  | "model"
  | "tool"
  | "termination";

export type ComponentConfigTypes =
  | TeamConfig
  | AgentConfig
  | ModelConfig
  | ToolConfig
  | TerminationConfig;

export interface BaseModelConfig extends BaseConfig {
  model: string;
  model_type: ModelTypes;
  api_key?: string;
  base_url?: string;
}

export interface AzureOpenAIModelConfig extends BaseModelConfig {
  model_type: "AzureOpenAIChatCompletionClient";
  azure_deployment: string;
  api_version: string;
  azure_endpoint: string;
  azure_ad_token_provider: string;
}

export interface OpenAIModelConfig extends BaseModelConfig {
  model_type: "OpenAIChatCompletionClient";
}

export type ModelConfig = AzureOpenAIModelConfig | OpenAIModelConfig;

export interface BaseToolConfig extends BaseConfig {
  name: string;
  description: string;
  content: string;
  tool_type: ToolTypes;
}

export interface PythonFunctionToolConfig extends BaseToolConfig {
  tool_type: "PythonFunction";
}

export type ToolConfig = PythonFunctionToolConfig;

export interface BaseAgentConfig extends BaseConfig {
  name: string;
  agent_type: AgentTypes;
  system_message?: string;
  model_client?: ModelConfig;
  tools?: ToolConfig[];
  description?: string;
}

export interface AssistantAgentConfig extends BaseAgentConfig {
  agent_type: "AssistantAgent";
}

export interface UserProxyAgentConfig extends BaseAgentConfig {
  agent_type: "UserProxyAgent";
}

export interface MultimodalWebSurferAgentConfig extends BaseAgentConfig {
  agent_type: "MultimodalWebSurfer";
}

export interface FileSurferAgentConfig extends BaseAgentConfig {
  agent_type: "FileSurfer";
}

export interface MagenticOneCoderAgentConfig extends BaseAgentConfig {
  agent_type: "MagenticOneCoderAgent";
}

export type AgentConfig =
  | AssistantAgentConfig
  | UserProxyAgentConfig
  | MultimodalWebSurferAgentConfig
  | FileSurferAgentConfig
  | MagenticOneCoderAgentConfig;

// export interface TerminationConfig extends BaseConfig {
//   termination_type: TerminationTypes;
//   max_messages?: number;
//   text?: string;
// }

export interface BaseTerminationConfig extends BaseConfig {
  termination_type: TerminationTypes;
}

export interface MaxMessageTerminationConfig extends BaseTerminationConfig {
  termination_type: "MaxMessageTermination";
  max_messages: number;
}

export interface TextMentionTerminationConfig extends BaseTerminationConfig {
  termination_type: "TextMentionTermination";
  text: string;
}

export interface CombinationTerminationConfig extends BaseTerminationConfig {
  termination_type: "CombinationTermination";
  operator: "and" | "or";
  conditions: TerminationConfig[];
}

export type TerminationConfig =
  | MaxMessageTerminationConfig
  | TextMentionTerminationConfig
  | CombinationTerminationConfig;

export interface BaseTeamConfig extends BaseConfig {
  name: string;
  participants: AgentConfig[];
  team_type: TeamTypes;
  termination_condition?: TerminationConfig;
}

export interface RoundRobinGroupChatConfig extends BaseTeamConfig {
  team_type: "RoundRobinGroupChat";
}

export interface SelectorGroupChatConfig extends BaseTeamConfig {
  team_type: "SelectorGroupChat";
  selector_prompt: string;
  model_client: ModelConfig;
}

export type TeamConfig = RoundRobinGroupChatConfig | SelectorGroupChatConfig;

export interface Team extends DBModel {
  config: TeamConfig;
}

export interface TeamResult {
  task_result: TaskResult;
  usage: string;
  duration: number;
}

export interface Run {
  id: string;
  created_at: string;
  updated_at?: string;
  status: RunStatus;
  task: AgentMessageConfig;
  team_result: TeamResult | null;
  messages: Message[]; // Change to Message[]
  error_message?: string;
}

export type RunStatus =
  | "created"
  | "active" // covers 'streaming'
  | "awaiting_input"
  | "timeout"
  | "complete"
  | "error"
  | "stopped";
