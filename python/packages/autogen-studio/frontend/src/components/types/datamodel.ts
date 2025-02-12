// Base Component System

export type ComponentTypes =
  | "team"
  | "agent"
  | "model"
  | "tool"
  | "termination";
export interface Component<T extends ComponentConfig> {
  provider: string;
  component_type: ComponentTypes;
  version?: number;
  component_version?: number;
  description?: string | null;
  config: T;
  label?: string;
}

// Message Types
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
  arguments: string;
  name: string;
}

export interface FunctionExecutionResult {
  call_id: string;
  content: string;
}

export interface BaseMessageConfig {
  source: string;
  models_usage?: RequestUsage;
}

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

export type AgentMessageConfig =
  | TextMessageConfig
  | MultiModalMessageConfig
  | StopMessageConfig
  | HandoffMessageConfig
  | ToolCallMessageConfig
  | ToolCallResultMessageConfig;

// Tool Configs
export interface FunctionToolConfig {
  source_code: string;
  name: string;
  description: string;
  global_imports: any[]; // Sequence[Import] equivalent
  has_cancellation_support: boolean;
}

// Provider-based Configs
export interface SelectorGroupChatConfig {
  participants: Component<AgentConfig>[];
  model_client: Component<ModelConfig>;
  termination_condition?: Component<TerminationConfig>;
  max_turns?: number;
  selector_prompt: string;
  allow_repeated_speaker: boolean;
}

export interface RoundRobinGroupChatConfig {
  participants: Component<AgentConfig>[];
  termination_condition?: Component<TerminationConfig>;
  max_turns?: number;
}

export interface MultimodalWebSurferConfig {
  name: string;
  model_client: Component<ModelConfig>;
  downloads_folder?: string;
  description?: string;
  debug_dir?: string;
  headless?: boolean;
  start_page?: string;
  animate_actions?: boolean;
  to_save_screenshots?: boolean;
  use_ocr?: boolean;
  browser_channel?: string;
  browser_data_dir?: string;
  to_resize_viewport?: boolean;
}

export interface AssistantAgentConfig {
  name: string;
  model_client: Component<ModelConfig>;
  tools?: Component<ToolConfig>[];
  handoffs?: any[]; // HandoffBase | str equivalent
  model_context?: Component<ChatCompletionContextConfig>;
  description: string;
  system_message?: string;
  reflect_on_tool_use: boolean;
  tool_call_summary_format: string;
}

export interface UserProxyAgentConfig {
  name: string;
  description: string;
}

// Model Configs
export interface ModelInfo {
  vision: boolean;
  function_calling: boolean;
  json_output: boolean;
  family: string;
}

export interface CreateArgumentsConfig {
  frequency_penalty?: number;
  logit_bias?: Record<string, number>;
  max_tokens?: number;
  n?: number;
  presence_penalty?: number;
  response_format?: any; // ResponseFormat equivalent
  seed?: number;
  stop?: string | string[];
  temperature?: number;
  top_p?: number;
  user?: string;
}

export interface BaseOpenAIClientConfig extends CreateArgumentsConfig {
  model: string;
  api_key?: string;
  timeout?: number;
  max_retries?: number;
  model_capabilities?: any; // ModelCapabilities equivalent
  model_info?: ModelInfo;
}

export interface OpenAIClientConfig extends BaseOpenAIClientConfig {
  organization?: string;
  base_url?: string;
}

export interface AzureOpenAIClientConfig extends BaseOpenAIClientConfig {
  azure_endpoint: string;
  azure_deployment?: string;
  api_version: string;
  azure_ad_token?: string;
  azure_ad_token_provider?: Component<any>;
}

export interface UnboundedChatCompletionContextConfig {
  // Empty in example but could have props
}

export interface OrTerminationConfig {
  conditions: Component<TerminationConfig>[];
}

export interface MaxMessageTerminationConfig {
  max_messages: number;
}

export interface TextMentionTerminationConfig {
  text: string;
}

// Config type unions based on provider
export type TeamConfig = SelectorGroupChatConfig | RoundRobinGroupChatConfig;

export type AgentConfig =
  | MultimodalWebSurferConfig
  | AssistantAgentConfig
  | UserProxyAgentConfig;

export type ModelConfig = OpenAIClientConfig | AzureOpenAIClientConfig;

export type ToolConfig = FunctionToolConfig;

export type ChatCompletionContextConfig = UnboundedChatCompletionContextConfig;

export type TerminationConfig =
  | OrTerminationConfig
  | MaxMessageTerminationConfig
  | TextMentionTerminationConfig;

export type ComponentConfig =
  | TeamConfig
  | AgentConfig
  | ModelConfig
  | ToolConfig
  | TerminationConfig
  | ChatCompletionContextConfig;

// DB Models
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

export interface Team extends DBModel {
  component: Component<TeamConfig>;
}

export interface Session extends DBModel {
  name: string;
  team_id?: number;
}

// Runtime Types
export interface SessionRuns {
  runs: Run[];
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
  messages: Message[];
  error_message?: string;
}

export type RunStatus =
  | "created"
  | "active"
  | "awaiting_input"
  | "timeout"
  | "complete"
  | "error"
  | "stopped";
