import { create } from "zustand";
import { getDefaultConfigFlows } from "../components/utils";
import { IChatMessage, IFlowConfig } from "../components/types";

interface ConfigState {
  flowConfigs: IFlowConfig[];
  setFlowConfigs: (flowConfigs: IFlowConfig[]) => void;
  flowConfig: IFlowConfig;
  setFlowConfig: (flowConfig: IFlowConfig) => void;
  messages: IChatMessage[];
  setMessages: (messages: IChatMessage[]) => void;
}

export const useConfigStore = create<ConfigState>()((set) => ({
  flowConfigs: getDefaultConfigFlows(),
  setFlowConfigs: (flowConfigs) => set({ flowConfigs }),
  flowConfig: getDefaultConfigFlows()[0],
  setFlowConfig: (flowConfig) => set({ flowConfig }),
  messages: [],
  setMessages: (messages) => set({ messages }),
}));
