export interface RequestUsage {
  prompt_tokens: number;
  completion_tokens: number;
}

export interface MessageConfig {
  source: string;
  content: string;
  models_usage?: RequestUsage;
}

export interface DBModel {
  id?: number;
  user_id?: string;
  created_at?: string;
  updated_at?: string;
}

export interface Message extends DBModel {
  config: MessageConfig;
  session_id: number;
  run_id: string;
}

export interface Session extends DBModel {
  name: string;
  team_id?: string;
}

export interface TeamConfig {
  name: string;
  participants: AgentConfig[];
  team_type: TeamTypes;
  model_client?: ModelConfig;
  termination_condition?: TerminationConfig;
}

export interface Team extends DBModel {
  config: TeamConfig;
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

export interface TaskResult {
  messages: MessageConfig[];
  usage: string;
  duration: number;
  stop_reason?: string;
}
