import { Settings } from "../../types/datamodel";
import { BaseAPI } from "../../utils/baseapi";

export class SettingsAPI extends BaseAPI {
  async getSettings(userId: string): Promise<Settings> {
    const response = await fetch(
      `${this.getBaseUrl()}/settings/?user_id=${userId}`,
      {
        headers: this.getHeaders(),
      }
    );
    const data = await response.json();
    if (!data.status)
      throw new Error(data.message || "Failed to fetch settings");
    return data.data;
  }

  async updateSettings(settings: Settings, userId: string): Promise<Settings> {
    const settingsData = {
      ...settings,
      user_id: settings.user_id || userId,
    };

    console.log("settingsData", settingsData);

    const response = await fetch(`${this.getBaseUrl()}/settings/`, {
      method: "PUT",
      headers: this.getHeaders(),
      body: JSON.stringify(settingsData),
    });
    const data = await response.json();
    if (!data.status)
      throw new Error(data.message || "Failed to update settings");
    return data.data;
  }
}

export const settingsAPI = new SettingsAPI();
