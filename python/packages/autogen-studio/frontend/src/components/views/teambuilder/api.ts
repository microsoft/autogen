import {
  Team,
  Component,
  ComponentConfig,
  McpServerParams,
} from "../../types/datamodel";
import { BaseAPI } from "../../utils/baseapi";
import { getServerUrl } from "../../utils/utils";

interface ValidationError {
  field: string;
  error: string;
  suggestion?: string;
}

export interface ValidationResponse {
  is_valid: boolean;
  errors: ValidationError[];
  warnings: ValidationError[];
}

export interface ComponentTestResult {
  status: boolean;
  message: string;
  data?: any;
  logs: string[];
}

// MCP-specific interfaces
export interface McpTool {
  name: string;
  description: string;
  parameters: {
    type: string;
    properties: Record<string, any>;
    required?: string[];
    additionalProperties?: boolean;
  };
}

export interface McpToolResult {
  name: string;
  result: Array<{ content: string }>;
  is_error: boolean;
}

export interface ListToolsResponse {
  status: boolean;
  message: string;
  tools?: McpTool[];
}

export interface CallToolResponse {
  status: boolean;
  message: string;
  result?: McpToolResult;
}

export class TeamAPI extends BaseAPI {
  async listTeams(userId: string): Promise<Team[]> {
    const response = await fetch(
      `${this.getBaseUrl()}/teams/?user_id=${userId}`,
      {
        headers: this.getHeaders(),
      }
    );
    const data = await response.json();
    if (!data.status) throw new Error(data.message || "Failed to fetch teams");
    return data.data;
  }

  async getTeam(teamId: number, userId: string): Promise<Team> {
    const response = await fetch(
      `${this.getBaseUrl()}/teams/${teamId}?user_id=${userId}`,
      {
        headers: this.getHeaders(),
      }
    );
    const data = await response.json();
    if (!data.status) throw new Error(data.message || "Failed to fetch team");
    return data.data;
  }

  async createTeam(teamData: Partial<Team>, userId: string): Promise<Team> {
    const team = {
      ...teamData,
      user_id: userId,
    };

    const response = await fetch(`${this.getBaseUrl()}/teams/`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(team),
    });
    const data = await response.json();
    if (!data.status) throw new Error(data.message || "Failed to create team");
    return data.data;
  }

  async deleteTeam(teamId: number, userId: string): Promise<void> {
    const response = await fetch(
      `${this.getBaseUrl()}/teams/${teamId}?user_id=${userId}`,
      {
        method: "DELETE",
        headers: this.getHeaders(),
      }
    );
    const data = await response.json();
    if (!data.status) throw new Error(data.message || "Failed to delete team");
  }
}

// move validationapi to its own class

export class ValidationAPI extends BaseAPI {
  async validateComponent(
    component: Component<ComponentConfig>
  ): Promise<ValidationResponse> {
    const response = await fetch(`${this.getBaseUrl()}/validate/`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({
        component: component,
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.message || "Failed to validate component");
    }

    return data;
  }

  async testComponent(
    component: Component<ComponentConfig>,
    timeout: number = 60
  ): Promise<ComponentTestResult> {
    const response = await fetch(`${this.getBaseUrl()}/validate/test`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify({
        component: component,
        timeout: timeout,
      }),
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.message || "Failed to test component");
    }

    return data;
  }
}

export class McpAPI extends BaseAPI {
  async listTools(serverParams: McpServerParams): Promise<ListToolsResponse> {
    const response = await fetch(`${this.getBaseUrl()}/mcp/tools`, {
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
}

export const teamAPI = new TeamAPI();
export const validationAPI = new ValidationAPI();
export const mcpAPI = new McpAPI();
