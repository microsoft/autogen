export type NotificationType = "success" | "info" | "warning" | "error";

export interface IMessage {
  userId: string;
  rootMsgId: string;
  msgId?: string;
  role: string;
  content: string;
  timestamp?: string;
  personalize?: boolean;
  use_cache?: boolean;
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
  msgId: string;
}

export interface ILLMConfig {
  seed: number;
  config_list: Array<{ [key: string]: any }>;
  temperature: number;
  use_cache: boolean;
}

export interface IAgentConfig {
  name: string;
  llm_config: ILLMConfig;
  human_input_mode: string;
  max_consecutive_auto_reply: number;
  system_message: string | null;
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
  receiver: IAgentFlowSpec | Array<IAgentFlowSpec>;
  type: "default" | "groupchat";
}
