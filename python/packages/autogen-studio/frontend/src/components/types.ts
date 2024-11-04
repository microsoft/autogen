export interface IStatus {
  message: string;
  status: boolean;
  data?: any;
}

export interface IMessageConfig {
  source: string;
  content: string;
}

export interface IDBModel {
  id?: number;
  user_id?: string;
  created_at?: string;
  updated_at?: string;
}

export interface IMessage extends IDBModel {
  config: IMessageConfig;
}

export interface ISession extends IDBModel {
  name: string;
}

export interface LogEvent {
  timestamp: string;
  type: string;
  content: string;
  source?: string;
}
