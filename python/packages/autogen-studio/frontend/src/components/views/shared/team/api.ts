import { Team, AgentConfig } from "../../../types/datamodel";
import { getServerUrl } from "../../../utils";

export class TeamAPI {
  private getBaseUrl(): string {
    return getServerUrl();
  }

  private getHeaders(): HeadersInit {
    return {
      "Content-Type": "application/json",
    };
  }

  async listTeams(userId: string): Promise<Team[]> {
    const response = await fetch(
      `${this.getBaseUrl()}/teams?user_id=${userId}`,
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

    const response = await fetch(`${this.getBaseUrl()}/teams`, {
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

  async linkAgentWithSequence(
    teamId: number,
    agentId: number,
    sequenceId: number
  ): Promise<void> {
    const response = await fetch(
      `${this.getBaseUrl()}/teams/${teamId}/agents/${agentId}/${sequenceId}`,
      {
        method: "POST",
        headers: this.getHeaders(),
      }
    );
    const data = await response.json();
    if (!data.status)
      throw new Error(
        data.message || "Failed to link agent to team with sequence"
      );
  }

  async unlinkAgent(teamId: number, agentId: number): Promise<void> {
    const response = await fetch(
      `${this.getBaseUrl()}/teams/${teamId}/agents/${agentId}`,
      {
        method: "DELETE",
        headers: this.getHeaders(),
      }
    );
    const data = await response.json();
    if (!data.status)
      throw new Error(data.message || "Failed to unlink agent from team");
  }

  async getTeamAgents(teamId: number): Promise<AgentConfig[]> {
    const response = await fetch(
      `${this.getBaseUrl()}/teams/${teamId}/agents`,
      {
        headers: this.getHeaders(),
      }
    );
    const data = await response.json();
    if (!data.status)
      throw new Error(data.message || "Failed to fetch team agents");
    return data.data;
  }
}

export const teamAPI = new TeamAPI();
