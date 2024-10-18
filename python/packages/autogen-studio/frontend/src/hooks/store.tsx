import { create } from "zustand";
import { v4 as uuidv4 } from "uuid";

import { IChatMessage, IChatSession } from "../components/types";

interface ConfigState {
  messages: IChatMessage[] | null;
  setMessages: (messages: IChatMessage[]) => void;
  session: IChatSession | null;
  setSession: (session: IChatSession | null) => void;
  sessions: IChatSession[];
  setSessions: (sessions: IChatSession[]) => void;
  version: string | null;
  setVersion: (version: string) => void;
  connectionId: string;
  setConnectionId: (connectionId: string) => void;
  areSessionButtonsDisabled: boolean;
  setAreSessionButtonsDisabled: (disabled: boolean) => void;
}

export const useConfigStore = create<ConfigState>()((set) => ({
  messages: null,
  setMessages: (messages) => set({ messages }),
  session: null,
  setSession: (session) => set({ session }),
  sessions: [],
  setSessions: (sessions) => set({ sessions }),
  version: null,
  setVersion: (version) => set({ version }),
  connectionId: uuidv4(),
  setConnectionId: (connectionId) => set({ connectionId }),
  areSessionButtonsDisabled: false,
  setAreSessionButtonsDisabled: (disabled) => set({ areSessionButtonsDisabled: disabled }),
}));
