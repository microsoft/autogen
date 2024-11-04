import { create } from "zustand";
import { v4 as uuidv4 } from "uuid";
import { IMessage, ISession } from "../components/types";

interface ISidebarState {
  isExpanded: boolean;
  isPinned: boolean;
}

export interface IConfigState {
  messages: IMessage[];
  setMessages: (messages: IMessage[]) => void;
  session: ISession | null;
  setSession: (session: ISession | null) => void;
  sessions: ISession[];
  setSessions: (sessions: ISession[]) => void;
  version: string | null;
  setVersion: (version: string | null) => void;

  // Sidebar state
  sidebar: ISidebarState;
  setSidebarState: (state: Partial<ISidebarState>) => void;
  collapseSidebar: () => void;
  expandSidebar: () => void;
  toggleSidebar: () => void;
}

export const useConfigStore = create<IConfigState>((set) => ({
  // Existing state
  messages: [],
  setMessages: (messages) => set({ messages }),
  session: null,
  setSession: (session) => set({ session }),
  sessions: [],
  setSessions: (sessions) => set({ sessions }),
  version: null,
  setVersion: (version) => set({ version }),
  connectionId: uuidv4(),

  // Sidebar state and actions
  sidebar: {
    isExpanded: true,
    isPinned: false,
  },

  setSidebarState: (newState) =>
    set((state) => ({
      sidebar: { ...state.sidebar, ...newState },
    })),

  collapseSidebar: () =>
    set((state) => ({
      sidebar: { ...state.sidebar, isExpanded: false },
    })),

  expandSidebar: () =>
    set((state) => ({
      sidebar: { ...state.sidebar, isExpanded: true },
    })),

  toggleSidebar: () =>
    set((state) => ({
      sidebar: { ...state.sidebar, isExpanded: !state.sidebar.isExpanded },
    })),
}));
