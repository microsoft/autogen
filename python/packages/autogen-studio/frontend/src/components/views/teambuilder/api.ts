import { Team, Component, ComponentConfig } from "../../types/datamodel";
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

  // Team-Agent Link Management
  async linkAgent(teamId: number, agentId: number): Promise<void> {
    const response = await fetch(
      `${this.getBaseUrl()}/teams/${teamId}/agents/${agentId}`,
      {
        method: "POST",
        headers: this.getHeaders(),
      }
    );
    const data = await response.json();
    if (!data.status)
      throw new Error(data.message || "Failed to link agent to team");
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
}

export const validationAPI = new ValidationAPI();

export const teamAPI = new TeamAPI();
