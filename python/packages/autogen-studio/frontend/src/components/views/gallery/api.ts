import { Gallery } from "../../types/datamodel";
import { BaseAPI } from "../../utils/baseapi";

export class GalleryAPI extends BaseAPI {
  async listGalleries(userId: string): Promise<Gallery[]> {
    const response = await fetch(
      `${this.getBaseUrl()}/gallery/?user_id=${userId}`,
      {
        headers: this.getHeaders(),
      }
    );
    const data = await response.json();
    if (!data.status)
      throw new Error(data.message || "Failed to fetch galleries");
    return data.data;
  }

  async getGallery(galleryId: number, userId: string): Promise<Gallery> {
    const response = await fetch(
      `${this.getBaseUrl()}/gallery/${galleryId}?user_id=${userId}`,
      {
        headers: this.getHeaders(),
      }
    );
    const data = await response.json();
    if (!data.status)
      throw new Error(data.message || "Failed to fetch gallery");
    return data.data;
  }

  async createGallery(
    galleryData: Partial<Gallery>,
    userId: string
  ): Promise<Gallery> {
    const gallery = {
      ...galleryData,
      user_id: userId,
    };

    console.log("Creating gallery with data:", gallery);

    const response = await fetch(`${this.getBaseUrl()}/gallery/`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(gallery),
    });
    const data = await response.json();
    if (!data.status)
      throw new Error(data.message || "Failed to create gallery");
    return data.data;
  }

  async updateGallery(
    galleryId: number,
    galleryData: Partial<Gallery>,
    userId: string
  ): Promise<Gallery> {
    const gallery = {
      ...galleryData,
      user_id: userId,
    };

    const response = await fetch(
      `${this.getBaseUrl()}/gallery/${galleryId}?user_id=${userId}`,
      {
        method: "PUT",
        headers: this.getHeaders(),
        body: JSON.stringify(gallery),
      }
    );
    const data = await response.json();
    if (!data.status)
      throw new Error(data.message || "Failed to update gallery");
    return data.data;
  }

  async deleteGallery(galleryId: number, userId: string): Promise<void> {
    const response = await fetch(
      `${this.getBaseUrl()}/gallery/${galleryId}?user_id=${userId}`,
      {
        method: "DELETE",
        headers: this.getHeaders(),
      }
    );
    const data = await response.json();
    if (!data.status)
      throw new Error(data.message || "Failed to delete gallery");
  }

  async syncGallery(url: string): Promise<Gallery> {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`Failed to sync gallery from ${url}`);
    }
    return await response.json();
  }
}

export const galleryAPI = new GalleryAPI();
