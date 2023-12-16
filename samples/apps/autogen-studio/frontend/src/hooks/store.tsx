import { create } from "zustand";

import { IChatMessage, IChatSession, IFlowConfig } from "../components/types";

interface ConfigState {
  workflowConfig: IFlowConfig | null;
  setWorkflowConfig: (flowConfig: IFlowConfig) => void;
  messages: IChatMessage[] | null;
  setMessages: (messages: IChatMessage[]) => void;
  session: IChatSession | null;
  setSession: (session: IChatSession) => void;
  sessions: IChatSession[];
  setSessions: (sessions: IChatSession[]) => void;
}

export const useConfigStore = create<ConfigState>()((set) => ({
  workflowConfig: null,
  setWorkflowConfig: (workflowConfig) => set({ workflowConfig }),
  messages: null,
  setMessages: (messages) => set({ messages }),
  session: null,
  setSession: (session) => set({ session }),
  sessions: [],
  setSessions: (sessions) => set({ sessions }),
}));
