import { GalleryConfig } from "../../types/datamodel";

// Load and parse the gallery JSON file
const loadGalleryFromJson = (): GalleryConfig => {
  try {
    // You can adjust the path to your JSON file as needed
    const galleryJson = require("./default_gallery.json");
    return galleryJson as GalleryConfig;
  } catch (error) {
    console.error("Error loading gallery JSON:", error);
    throw error;
  }
};

export const defaultGallery: GalleryConfig = loadGalleryFromJson();
