import {
  Workflow,
  CreateWorkflowRequest,
  UpdateWorkflowRequest,
} from "./types";
import { BaseAPI } from "../../utils/baseapi";

export class WorkflowAPI extends BaseAPI {
  async getWorkflows(userId: string): Promise<Workflow[]> {
    const response = await fetch(
      `${this.getBaseUrl()}/workflows?user_id=${userId}`,
      {
        headers: this.getHeaders(),
      }
    );
    const data = await response.json();
    console.log("getWorkflows response:", data);
    if (!data.status)
      throw new Error(data.message || "Failed to fetch workflows");

    // Return backend data directly
    return data.data;
  }

  async getWorkflow(id: number, userId: string): Promise<Workflow> {
    const response = await fetch(
      `${this.getBaseUrl()}/workflows/${id}?user_id=${userId}`,
      {
        headers: this.getHeaders(),
      }
    );
    const data = await response.json();
    if (!data.status)
      throw new Error(data.message || "Failed to fetch workflow");

    return data.data;
  }

  async createWorkflow(
    workflowData: CreateWorkflowRequest,
    userId: string
  ): Promise<Workflow> {
    const backendRequest = {
      name: workflowData.name,
      description: workflowData.description,
      config: workflowData.config,
      tags: [],
      user_id: userId,
    };

    const response = await fetch(`${this.getBaseUrl()}/workflows`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(backendRequest),
    });
    const data = await response.json();
    if (!data.status)
      throw new Error(data.message || "Failed to create workflow");

    // Return the created workflow by fetching it
    return this.getWorkflow(data.data.workflow_id.toString(), userId);
  }

  async updateWorkflow(
    id: number,
    workflowData: UpdateWorkflowRequest,
    userId: string
  ): Promise<Workflow> {
    const backendRequest = {
      name: workflowData.name,
      description: workflowData.description,
      config: workflowData.config,
    };

    const response = await fetch(
      `${this.getBaseUrl()}/workflows/${id}?user_id=${userId}`,
      {
        method: "PUT",
        headers: this.getHeaders(),
        body: JSON.stringify(backendRequest),
      }
    );
    const data = await response.json();
    if (!data.status)
      throw new Error(data.message || "Failed to update workflow");

    return data.data;
  }

  async deleteWorkflow(id: number, userId: string): Promise<boolean> {
    const response = await fetch(
      `${this.getBaseUrl()}/workflows/${id}?user_id=${userId}`,
      {
        method: "DELETE",
        headers: this.getHeaders(),
      }
    );
    const data = await response.json();
    if (!data.status)
      throw new Error(data.message || "Failed to delete workflow");

    return true;
  }

  async createWorkflowRun(
    workflowId?: number,
    workflowConfig?: any
  ): Promise<any> {
    const request: any = {};

    if (workflowId) {
      request.workflow_id = workflowId;
    } else if (workflowConfig) {
      request.workflow_config = workflowConfig;
    } else {
      throw new Error("Either workflow_id or workflow_config must be provided");
    }

    const response = await fetch(`${this.getBaseUrl()}/workflows/run`, {
      method: "POST",
      headers: this.getHeaders(),
      body: JSON.stringify(request),
    });
    const data = await response.json();
    if (!data.status)
      throw new Error(data.message || "Failed to create workflow run");

    return data;
  }

  async getSteps(): Promise<any[]> {
    const response = await fetch(
      `${this.getBaseUrl()}/workflows/library/steps`,
      {
        headers: this.getHeaders(),
      }
    );
    const data = await response.json();
    console.log("getSteps response:", data);
    if (!data.status) throw new Error(data.message || "Failed to fetch steps");

    // Return backend ComponentModel objects directly
    return data.data;
  }

  async getStepLibrary(): Promise<any[]> {
    const response = await fetch(
      `${this.getBaseUrl()}/workflows/library/steps`,
      {
        headers: this.getHeaders(),
      }
    );
    const data = await response.json();
    if (!data.status)
      throw new Error(data.message || "Failed to fetch step library");

    // Return backend ComponentModel array directly
    return data.data;
  }
}

export const workflowAPI = new WorkflowAPI();
