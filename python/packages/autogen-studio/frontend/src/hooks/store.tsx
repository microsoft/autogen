import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { v4 as uuidv4 } from "uuid";
import { Message, Session } from "../components/types/datamodel";

interface IBreadcrumb {
  name: string;
  href: string;
  current?: boolean;
}

// New interfaces
export interface IAgentFlowSettings {
  direction: "TB" | "LR";
  showLabels: boolean;
  showGrid: boolean;
  showTokens: boolean;
  showMessages: boolean;
  // Add any other settings we want to persist
}

interface IHeaderState {
  title: string;
  breadcrumbs?: IBreadcrumb[];
}

interface ISidebarState {
  isExpanded: boolean;
  isPinned: boolean;
}

export interface IConfigState {
  messages: Message[];
  setMessages: (messages: Message[]) => void;
  session: Session | null;
  setSession: (session: Session | null) => void;
  sessions: Session[];
  setSessions: (sessions: Session[]) => void;
  version: string | null;
  setVersion: (version: string | null) => void;

  // Header state
  header: IHeaderState;
  setHeader: (header: Partial<IHeaderState>) => void;
  setBreadcrumbs: (breadcrumbs: IBreadcrumb[]) => void;

  // Sidebar state
  sidebar: ISidebarState;
  setSidebarState: (state: Partial<ISidebarState>) => void;
  collapseSidebar: () => void;
  expandSidebar: () => void;
  toggleSidebar: () => void;

  // Agent flow settings agentFlow: IAgentFlowSettings;
  agentFlow: IAgentFlowSettings;
  setAgentFlowSettings: (settings: Partial<IAgentFlowSettings>) => void;
}

// Default settings
const DEFAULT_AGENT_FLOW_SETTINGS: IAgentFlowSettings = {
  direction: "TB",
  showLabels: true,
  showGrid: true,
  showTokens: true,
  showMessages: true,
};

export const useConfigStore = create<IConfigState>()(
  persist(
    (set) => ({
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

      // Header state
      header: {
        title: "",
        breadcrumbs: [],
      },
      setHeader: (newHeader) =>
        set((state) => ({
          header: { ...state.header, ...newHeader },
        })),
      setBreadcrumbs: (breadcrumbs) =>
        set((state) => ({
          header: { ...state.header, breadcrumbs },
        })),
      // Add AgentFlow settings
      agentFlow: DEFAULT_AGENT_FLOW_SETTINGS,
      setAgentFlowSettings: (newSettings) =>
        set((state) => ({
          agentFlow: { ...state.agentFlow, ...newSettings },
        })),

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
    }),
    {
      name: "app-sidebar-state",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        sidebar: state.sidebar,
        agentFlow: state.agentFlow,
      }),
    }
  )
);
