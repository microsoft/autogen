export type NotificationType = "success" | "info" | "warning" | "error";

export interface IImageGeneratorConfig {
  prompt: string;
  n: number;
  width: number;
  height: number;
}

export interface IMessage {
  userId: string;
  rootMsgId: number;
  msgId: number;
  role: string;
  content: string;
  timestamp: string;
  personalize?: boolean;
  use_cache?: boolean;
  ra?: string;
}

export interface ITextGeneratorConfig {
  prompt?: string;
  max_tokens?: number;
  temperature: number;
  messages: any[];
  n: number;
  model?: string;
  suffix?: string;
  presence_penalty?: number;
  frequency_penalty?: number;
  input?: string;
  instruction?: string;
}
export interface IMetaDataConfig {
  ranker: string;
  prompter: string;
  top_k: number;
}
export interface IGenConfig {
  metadata: IMetaDataConfig;
  textgen_config: ITextGeneratorConfig;
  use_cache?: boolean;
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
  msgId: number;
}
export interface IContext {
  source: string;
  content: string;
}
export interface IContextProps {
  context: IContextItem | null;
  setContext: React.Dispatch<React.SetStateAction<IContextItem | null>>;
}
export interface IBlock {
  id: string;
  tag: string;
  html: string;
}

// Context interfaces

export interface IContextItem {
  id: number;
  title: string;
  user_guid: number;
  guid: string;
  index_path: string;
  created_at: string;
  updated_at: string;
}

export interface IContextDocumentItem {
  id?: number;
  title: string;
  source: string;
  content: string;
  document_type: string;
  context_guid?: string;
  guid?: string;
  url?: string;
  created_at?: string;
  updated_at?: string;
  status?: string;
  num_passages?: number;
}
