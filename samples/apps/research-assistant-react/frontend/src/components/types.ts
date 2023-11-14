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
  seed: number;
  config_list: Array<{ [key: string]: any }>;
  temperature: number;
}

export interface IAgentConfig {
  name: string;
  llm_config: ILLMConfig;
  human_input_mode: string;
  max_consecutive_auto_reply: number;
  system_message: string | "";
  is_termination_msg?: boolean | string;
  code_execution_config?: boolean | string | { [key: string]: any } | null;
}

export interface IAgentFlowSpec {
  type: "assistant" | "user_proxy" | "group_chat";
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
  api_key: string;
  api_version: string;
  api_base: string;
}
