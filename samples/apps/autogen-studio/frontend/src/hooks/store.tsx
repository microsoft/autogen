import { create } from "zustand";

import { IChatMessage, IChatSession, IFlowConfig } from "../components/types";

interface ConfigState {
  workflowConfig: IFlowConfig | null;
  setWorkflowConfig: (flowConfig: IFlowConfig | null) => void;
  messages: IChatMessage[] | null;
  setMessages: (messages: IChatMessage[]) => void;
  session: IChatSession | null;
  setSession: (session: IChatSession | null) => void;
  sessions: IChatSession[];
  setSessions: (sessions: IChatSession[]) => void;
  version: string | null;
  setVersion: (version: string) => void;
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
  version: null,
  setVersion: (version) => set({ version }),
}));
