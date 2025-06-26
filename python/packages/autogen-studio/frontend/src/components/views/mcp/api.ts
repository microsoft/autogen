import { Gallery, Component, McpWorkbenchConfig } from "../../types/datamodel";
import { BaseAPI } from "../../utils/baseapi";

export class McpAPI extends BaseAPI {
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

  // Helper function to extract MCP workbenches from a gallery
  extractMcpWorkbenches(gallery: Gallery): Component<McpWorkbenchConfig>[] {
    return (
      gallery.config.components.workbenches?.filter(
        (workbench): workbench is Component<McpWorkbenchConfig> =>
          workbench.provider.includes("McpWorkbench") ||
          (workbench.config as any)?.server_params !== undefined
      ) || []
    );
  }

  // Test MCP server connection (placeholder for now)
  async testMcpConnection(
    workbench: Component<McpWorkbenchConfig>
  ): Promise<boolean> {
    // This is a placeholder - in the future, this would make an actual call to test the MCP server
    await new Promise((resolve) => setTimeout(resolve, 1000));
    return Math.random() > 0.3; // 70% success rate for testing
  }
}

export const mcpAPI = new McpAPI();
