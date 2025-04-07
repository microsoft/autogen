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

export interface BaseAgentEvent extends BaseMessageConfig {}

export interface ModelClientStreamingChunkEvent extends BaseAgentEvent {
  content: string;
  type: "ModelClientStreamingChunkEvent";
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
  | ToolCallResultMessageConfig
  | ModelClientStreamingChunkEvent;

export interface FromModuleImport {
  module: string;
  imports: string[];
}

// Import can be either a string (direct import) or a FromModuleImport
export type Import = string | FromModuleImport;

// Code Executor Base Config
export interface CodeExecutorBaseConfig {
  timeout?: number;
  work_dir?: string;
}

// Local Command Line Code Executor Config
export interface LocalCommandLineCodeExecutorConfig
  extends CodeExecutorBaseConfig {
  functions_module?: string;
}

// Docker Command Line Code Executor Config
export interface DockerCommandLineCodeExecutorConfig
  extends CodeExecutorBaseConfig {
  image?: string;
  container_name?: string;
  bind_dir?: string;
  auto_remove?: boolean;
  stop_container?: boolean;
  functions_module?: string;
  extra_volumes?: Record<string, Record<string, string>>;
  extra_hosts?: Record<string, string>;
  init_command?: string;
}

// Jupyter Code Executor Config
export interface JupyterCodeExecutorConfig extends CodeExecutorBaseConfig {
  kernel_name?: string;
  output_dir?: string;
}

// Python Code Execution Tool Config
export interface PythonCodeExecutionToolConfig {
  executor: Component<
    | LocalCommandLineCodeExecutorConfig
    | DockerCommandLineCodeExecutorConfig
    | JupyterCodeExecutorConfig
  >;
  description?: string;
  name?: string;
}

// The complete FunctionToolConfig interface
export interface FunctionToolConfig {
  source_code: string;
  name: string;
  description: string;
  global_imports: Import[];
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
  model_client_stream: boolean;
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

export interface BaseAnthropicClientConfig extends CreateArgumentsConfig {
  model: string;
  api_key?: string;
  base_url?: string;
  model_capabilities?: any; // ModelCapabilities equivalent
  model_info?: ModelInfo;
  timeout?: number;
  max_retries?: number;
  default_headers?: Record<string, string>;
  max_tokens?: number;
  temperature?: number;
  top_p?: number;
  top_k?: number;
  stop_sequences?: string | string[];
  response_format?: any; // ResponseFormat equivalent
  metadata?: Record<string, string>;
}

export interface AnthropicClientConfig extends BaseAnthropicClientConfig {
  tools?: Array<Record<string, any>>;
  tool_choice?: "auto" | "any" | "none" | Record<string, any>;
}

export interface UnboundedChatCompletionContextConfig {
  // Empty in example but could have props
}

export interface OrTerminationConfig {
  conditions: Component<TerminationConfig>[];
}

export interface AndTerminationConfig {
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

export type ModelConfig =
  | OpenAIClientConfig
  | AzureOpenAIClientConfig
  | AnthropicClientConfig;

export type ToolConfig = FunctionToolConfig | PythonCodeExecutionToolConfig;

export type ChatCompletionContextConfig = UnboundedChatCompletionContextConfig;

export type TerminationConfig =
  | OrTerminationConfig
  | AndTerminationConfig
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
  run_id: number;
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
  type:
    | "message"
    | "result"
    | "completion"
    | "input_request"
    | "error"
    | "llm_call_event"
    | "message_chunk";
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
  id: number;
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

// Settings

export type EnvironmentVariableType =
  | "string"
  | "number"
  | "boolean"
  | "secret";

export interface EnvironmentVariable {
  name: string;
  value: string;
  type: EnvironmentVariableType;
  description?: string;
  required: boolean;
}

export interface UISettings {
  show_llm_call_events: boolean;
  expanded_messages_by_default?: boolean;
  show_agent_flow_by_default?: boolean;
  // You can add more UI settings here as needed
}

export interface SettingsConfig {
  environment: EnvironmentVariable[];
  default_model_client?: Component<ModelConfig>;
  ui: UISettings;
}

export interface Settings extends DBModel {
  config: SettingsConfig;
}

export interface GalleryMetadata {
  author: string;
  created_at: string;
  updated_at: string;
  version: string;
  description?: string;
  tags?: string[];
  license?: string;
  homepage?: string;
  category?: string;
  lastSynced?: string;
}

export interface GalleryConfig {
  id: string;
  name: string;
  url?: string;
  metadata: GalleryMetadata;
  components: {
    teams: Component<TeamConfig>[];
    agents: Component<AgentConfig>[];
    models: Component<ModelConfig>[];
    tools: Component<ToolConfig>[];
    terminations: Component<TerminationConfig>[];
  };
}

export interface Gallery extends DBModel {
  config: GalleryConfig;
}
