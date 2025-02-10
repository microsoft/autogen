import { create } from "zustand";
import { persist } from "zustand/middleware";
import { Gallery } from "./types";
import {
  AgentConfig,
  Component,
  ModelConfig,
  TeamConfig,
  TerminationConfig,
  ToolConfig,
} from "../../types/datamodel";
import { defaultGallery } from "./utils";

interface GalleryStore {
  galleries: Gallery[];
  defaultGalleryId: string;
  selectedGalleryId: string | null;

  addGallery: (gallery: Gallery) => void;
  updateGallery: (id: string, gallery: Partial<Gallery>) => void;
  removeGallery: (id: string) => void;
  setDefaultGallery: (id: string) => void;
  selectGallery: (id: string) => void;
  getDefaultGallery: () => Gallery;
  getSelectedGallery: () => Gallery | null;
  syncGallery: (id: string) => Promise<void>;
  getLastSyncTime: (id: string) => string | null;
  getGalleryComponents: () => {
    teams: Component<TeamConfig>[];
    components: {
      agents: Component<AgentConfig>[];
      models: Component<ModelConfig>[];
      tools: Component<ToolConfig>[];
      terminations: Component<TerminationConfig>[];
    };
  };
}

export const useGalleryStore = create<GalleryStore>()(
  persist(
    (set, get) => ({
      galleries: [defaultGallery],
      defaultGalleryId: defaultGallery.id,
      selectedGalleryId: defaultGallery.id,

      addGallery: (gallery) =>
        set((state) => {
          if (state.galleries.find((g) => g.id === gallery.id)) return state;
          return {
            galleries: [gallery, ...state.galleries],
            defaultGalleryId: state.defaultGalleryId || gallery.id,
            selectedGalleryId: state.selectedGalleryId || gallery.id,
          };
        }),

      updateGallery: (id, updates) =>
        set((state) => ({
          galleries: state.galleries.map((gallery) =>
            gallery.id === id
              ? {
                  ...gallery,
                  ...updates,
                  metadata: {
                    ...gallery.metadata,
                    ...updates.metadata,
                    updated_at: new Date().toISOString(),
                  },
                }
              : gallery
          ),
        })),

      removeGallery: (id) =>
        set((state) => {
          if (state.galleries.length <= 1) return state;

          const newGalleries = state.galleries.filter((g) => g.id !== id);
          const updates: Partial<GalleryStore> = {
            galleries: newGalleries,
          };

          if (id === state.defaultGalleryId) {
            updates.defaultGalleryId = newGalleries[0].id;
          }

          if (id === state.selectedGalleryId) {
            updates.selectedGalleryId = newGalleries[0].id;
          }

          return updates;
        }),

      setDefaultGallery: (id) =>
        set((state) => {
          const gallery = state.galleries.find((g) => g.id === id);
          if (!gallery) return state;
          return { defaultGalleryId: id };
        }),

      selectGallery: (id) =>
        set((state) => {
          const gallery = state.galleries.find((g) => g.id === id);
          if (!gallery) return state;
          return { selectedGalleryId: id };
        }),

      getDefaultGallery: () => {
        const { galleries, defaultGalleryId } = get();
        return galleries.find((g) => g.id === defaultGalleryId)!;
      },

      getSelectedGallery: () => {
        const { galleries, selectedGalleryId } = get();
        if (!selectedGalleryId) return null;
        return galleries.find((g) => g.id === selectedGalleryId) || null;
      },

      syncGallery: async (id) => {
        const gallery = get().galleries.find((g) => g.id === id);
        if (!gallery?.url) return;

        try {
          const response = await fetch(gallery.url);
          const remoteGallery = await response.json();

          get().updateGallery(id, {
            ...remoteGallery,
            id, // preserve local id
            metadata: {
              ...remoteGallery.metadata,
              lastSynced: new Date().toISOString(),
            },
          });
        } catch (error) {
          console.error("Failed to sync gallery:", error);
          throw error;
        }
      },

      getLastSyncTime: (id) => {
        const gallery = get().galleries.find((g) => g.id === id);
        return gallery?.metadata.lastSynced ?? null;
      },

      getGalleryComponents: () => {
        const defaultGallery = get().getDefaultGallery();
        return {
          teams: defaultGallery.items.teams,
          components: defaultGallery.items.components,
        };
      },
    }),
    {
      name: "gallery-storage-v6",
    }
  )
);
