export type NotificationType = "success" | "info" | "warning" | "error";

export interface IMessage {
  user_id: string;
  root_msg_id: string;
  msg_id?: string;
  role: string;
  content: string;
  timestamp?: string;
  personalize?: boolean;
  ra?: string;
}

export interface IStatus {
  message: string;
  status: boolean;
  data?: any;
}

export interface IChatMessage {
  text: string;
  sender: "user" | "bot";
  metadata?: any;
  msg_id: string;
}

export interface ILLMConfig {
  config_list: Array<IModelConfig>;
  timeout?: number;
  cache_seed?: number | null;
  temperature: number;
}

export interface IAgentConfig {
  name: string;
  llm_config?: ILLMConfig;
  human_input_mode: string;
  max_consecutive_auto_reply: number;
  system_message: string | "";
  is_termination_msg?: boolean | string;
  code_execution_config?: boolean | string | { [key: string]: any } | null;
}

export interface IAgentFlowSpec {
  type: "assistant" | "userproxy" | "groupchat";
  config: IAgentConfig;
}

export interface IFlowConfig {
  name: string;
  sender: IAgentFlowSpec;
  receiver: IAgentFlowSpec;
  type: "default" | "groupchat";
}

export interface IModelConfig {
  model: string;
  api_key?: string;
  api_version?: string;
  base_url?: string;
  api_type?: string;
}
