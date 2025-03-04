// store.tsx
import { create } from "zustand";
import { persist } from "zustand/middleware";
import { settingsAPI } from "./api";
import { Settings, UISettings } from "../../types/datamodel";

// Default UI settings that match the backend defaults
const DEFAULT_UI_SETTINGS: UISettings = {
  show_llm_call_events: false,
  expanded_messages_by_default: false,
  show_agent_flow_by_default: false,
};

interface SettingsState {
  // Server-synced settings
  serverSettings: Settings | null;
  isLoading: boolean;
  error: string | null;

  // UI settings - these will be synced with server but kept in local state for performance
  uiSettings: UISettings;

  // Actions
  initializeSettings: (userId: string) => Promise<void>;
  updateUISettings: (settings: Partial<UISettings>) => void; // Simplified to avoid async issues
  resetUISettings: () => Promise<void>;
}

// Helper function to safely access nested properties
const getUISettings = (settings: Settings | null): UISettings => {
  if (!settings || !settings.config || !settings.config.ui) {
    return DEFAULT_UI_SETTINGS;
  }
  return settings.config.ui;
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, get) => ({
      // Initial state
      serverSettings: null,
      isLoading: false,
      error: null,
      uiSettings: DEFAULT_UI_SETTINGS,

      // Load settings from server
      initializeSettings: async (userId: string) => {
        // Skip if already loading
        if (get().isLoading) return;

        try {
          set({ isLoading: true, error: null });
          const settings = await settingsAPI.getSettings(userId);

          // Extract UI settings from server response
          const uiSettings = getUISettings(settings);

          set({
            serverSettings: settings,
            uiSettings,
            isLoading: false,
          });
        } catch (error) {
          console.error("Failed to load settings:", error);
          set({
            error: "Failed to load settings",
            isLoading: false,
            // Use defaults if server fails
            uiSettings: DEFAULT_UI_SETTINGS,
          });
        }
      },

      // Update UI settings locally only
      // The UISettingsPanel component will handle server syncing
      updateUISettings: (partialSettings: Partial<UISettings>) => {
        const { uiSettings } = get();
        const newUISettings = { ...uiSettings, ...partialSettings };
        set({ uiSettings: newUISettings });
      },

      // Reset UI settings to defaults - now just resets local state
      // The UISettingsPanel component will handle actual server resets
      resetUISettings: async () => {
        set({ uiSettings: DEFAULT_UI_SETTINGS });
        return Promise.resolve();
      },
    }),
    {
      name: "ags-app-settings-0",
      partialize: (state) => ({
        // Only persist UI settings locally for performance
        uiSettings: state.uiSettings,
      }),
    }
  )
);
