//settings/store.tsx
import { create } from "zustand";
import { persist } from "zustand/middleware";

interface PlaygroundSettings {
  showLLMEvents: boolean;
  // Future playground settings
  expandedMessagesByDefault?: boolean;
  showAgentFlowByDefault?: boolean;
}

interface TeamBuilderSettings {
  // Future teambuilder settings
  showAdvancedOptions?: boolean;
  defaultAgentLayout?: "grid" | "list";
}

interface GallerySettings {
  // Future gallery settings
  viewMode?: "grid" | "list";
  sortBy?: "date" | "popularity";
}

interface SettingsState {
  playground: PlaygroundSettings;
  teamBuilder: TeamBuilderSettings;
  gallery: GallerySettings;
  // Actions to update settings
  updatePlaygroundSettings: (settings: Partial<PlaygroundSettings>) => void;
  updateTeamBuilderSettings: (settings: Partial<TeamBuilderSettings>) => void;
  updateGallerySettings: (settings: Partial<GallerySettings>) => void;
  // Reset functions
  resetPlaygroundSettings: () => void;
  resetTeamBuilderSettings: () => void;
  resetGallerySettings: () => void;
  resetAllSettings: () => void;
}

const DEFAULT_PLAYGROUND_SETTINGS: PlaygroundSettings = {
  showLLMEvents: true, // Default to hiding LLM events
};

const DEFAULT_TEAMBUILDER_SETTINGS: TeamBuilderSettings = {
  showAdvancedOptions: false,
  defaultAgentLayout: "grid",
};

const DEFAULT_GALLERY_SETTINGS: GallerySettings = {
  viewMode: "grid",
  sortBy: "date",
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set) => ({
      // Initial state
      playground: DEFAULT_PLAYGROUND_SETTINGS,
      teamBuilder: DEFAULT_TEAMBUILDER_SETTINGS,
      gallery: DEFAULT_GALLERY_SETTINGS,

      // Update functions
      updatePlaygroundSettings: (settings) =>
        set((state) => ({
          playground: { ...state.playground, ...settings },
        })),

      updateTeamBuilderSettings: (settings) =>
        set((state) => ({
          teamBuilder: { ...state.teamBuilder, ...settings },
        })),

      updateGallerySettings: (settings) =>
        set((state) => ({
          gallery: { ...state.gallery, ...settings },
        })),

      // Reset functions
      resetPlaygroundSettings: () =>
        set((state) => ({
          playground: DEFAULT_PLAYGROUND_SETTINGS,
        })),

      resetTeamBuilderSettings: () =>
        set((state) => ({
          teamBuilder: DEFAULT_TEAMBUILDER_SETTINGS,
        })),

      resetGallerySettings: () =>
        set((state) => ({
          gallery: DEFAULT_GALLERY_SETTINGS,
        })),

      resetAllSettings: () =>
        set({
          playground: DEFAULT_PLAYGROUND_SETTINGS,
          teamBuilder: DEFAULT_TEAMBUILDER_SETTINGS,
          gallery: DEFAULT_GALLERY_SETTINGS,
        }),
    }),
    {
      name: "ags-app-settings",
      partialize: (state) => ({
        playground: state.playground,
        teamBuilder: state.teamBuilder,
        gallery: state.gallery,
      }),
    }
  )
);

// Example usage:
/*
import { useSettingsStore } from './stores/settings';

// In a component:
const { showLLMEvents } = useSettingsStore((state) => state.playground);
const updatePlaygroundSettings = useSettingsStore((state) => state.updatePlaygroundSettings);

// Toggle LLM events
updatePlaygroundSettings({ showLLMEvents: !showLLMEvents });
*/
