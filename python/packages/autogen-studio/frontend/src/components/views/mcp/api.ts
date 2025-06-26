import {
  Gallery,
  Component,
  McpWorkbenchConfig,
  McpServerParams,
} from "../../types/datamodel";
import { BaseAPI } from "../../utils/baseapi";

// MCP-specific interfaces for server operations
// MCP types matching backend exactly (native MCP types)
export interface Tool {
  name: string;
  description?: string | null;
  inputSchema: {
    [key: string]: any;
  };
  annotations?: {
    title?: string | null;
    readOnlyHint?: boolean | null;
    destructiveHint?: boolean | null;
    idempotentHint?: boolean | null;
    openWorldHint?: boolean | null;
  } | null;
}

export interface CallToolResult {
  content: Array<{
    type: "text" | "image" | "resource";
    text?: string;
    data?: string;
    mimeType?: string;
    resource?: any;
    annotations?: any;
  }>;
  isError?: boolean;
}

export interface ListToolsResponse {
  status: boolean;
  message: string;
  tools?: Tool[];
}

export interface CallToolResponse {
  status: boolean;
  message: string;
  result?: CallToolResult;
}

export class McpAPI extends BaseAPI {
  // Gallery management methods (existing functionality)
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

  // MCP Server operations (new functionality)
  async listTools(serverParams: McpServerParams): Promise<ListToolsResponse> {
    const response = await fetch(`${this.getBaseUrl()}/mcp/tools/list`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({ server_params: serverParams }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.message || "Failed to list MCP tools");
    }

    return data;
  }

  async callTool(
    serverParams: McpServerParams,
    toolName: string,
    toolArguments: Record<string, any>
  ): Promise<CallToolResponse> {
    const response = await fetch(`${this.getBaseUrl()}/mcp/tools/call`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({
        server_params: serverParams,
        tool_name: toolName,
        arguments: toolArguments,
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.message || "Failed to call MCP tool");
    }

    return data;
  }

  async healthCheck(): Promise<{ status: boolean; message: string }> {
    const response = await fetch(`${this.getBaseUrl()}/mcp/health`, {
      method: "GET",
      headers: this.getHeaders(),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.message || "MCP health check failed");
    }

    return data;
  }

  // Test MCP server connection
  async testMcpConnection(
    workbench: Component<McpWorkbenchConfig>
  ): Promise<boolean> {
    try {
      // Use the health check or list tools to test connection
      if (workbench.config.server_params) {
        const result = await this.listTools(workbench.config.server_params);
        return result.status;
      }
      return false;
    } catch (error) {
      console.error("MCP connection test failed:", error);
      return false;
    }
  }
}

export const mcpAPI = new McpAPI();
