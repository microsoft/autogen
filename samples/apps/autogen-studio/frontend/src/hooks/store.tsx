import { create } from "zustand";
import { getDefaultConfigFlows } from "../components/utils";
import { IChatMessage, IChatSession, IFlowConfig } from "../components/types";

interface ConfigState {
  flowConfigs: IFlowConfig[];
  setFlowConfigs: (flowConfigs: IFlowConfig[]) => void;
  flowConfig: IFlowConfig;
  setFlowConfig: (flowConfig: IFlowConfig) => void;
  messages: IChatMessage[] | null;
  setMessages: (messages: IChatMessage[]) => void;
  session: IChatSession | null;
  setSession: (session: IChatSession) => void;
  sessions: IChatSession[];
  setSessions: (sessions: IChatSession[]) => void;
}

export const useConfigStore = create<ConfigState>()((set) => ({
  flowConfigs: getDefaultConfigFlows(),
  setFlowConfigs: (flowConfigs) => set({ flowConfigs }),
  flowConfig: getDefaultConfigFlows()[0],
  setFlowConfig: (flowConfig) => set({ flowConfig }),
  messages: null,
  setMessages: (messages) => set({ messages }),
  session: null,
  setSession: (session) => set({ session }),
  sessions: [],
  setSessions: (sessions) => set({ sessions }),
}));
