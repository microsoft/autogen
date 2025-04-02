import { create } from "zustand";
import { Gallery } from "../../types/datamodel";
import { galleryAPI } from "./api";

interface GalleryState {
  // State
  galleries: Gallery[];
  selectedGallery: Gallery | null;
  isLoading: boolean;
  error: string | null;

  // Actions
  fetchGalleries: (userId: string) => Promise<void>;
  selectGallery: (gallery: Gallery) => void;
  getSelectedGallery: () => Gallery | null;
}

export const useGalleryStore = create<GalleryState>((set, get) => ({
  // Initial state
  galleries: [],
  selectedGallery: null,
  isLoading: false,
  error: null,

  // Actions
  fetchGalleries: async (userId: string) => {
    try {
      set({ isLoading: true, error: null });
      const galleries = await galleryAPI.listGalleries(userId);

      set({
        galleries,
        // Automatically select first gallery if none selected
        selectedGallery: get().selectedGallery || galleries[0] || null,
        isLoading: false,
      });
    } catch (error) {
      set({
        error:
          error instanceof Error ? error.message : "Failed to fetch galleries",
        isLoading: false,
      });
    }
  },

  selectGallery: (gallery: Gallery) => {
    set({ selectedGallery: gallery });
  },

  getSelectedGallery: () => {
    return get().selectedGallery;
  },
}));
