import { Gallery } from "./types";

// Load and parse the gallery JSON file
const loadGalleryFromJson = (): Gallery => {
  try {
    // You can adjust the path to your JSON file as needed
    const galleryJson = require("./default_gallery.json");
    return galleryJson as Gallery;
  } catch (error) {
    console.error("Error loading gallery JSON:", error);
    throw error;
  }
};

export const defaultGallery: Gallery = loadGalleryFromJson();
