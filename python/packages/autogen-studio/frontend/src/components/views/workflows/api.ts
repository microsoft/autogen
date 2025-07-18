import {
  Workflow,
  Step,
  StepLibrary,
  ApiResponse,
  CreateWorkflowRequest,
  UpdateWorkflowRequest,
  WorkflowConfig,
  WorkflowRun,
} from "./types";

// Mock data for development
const mockSteps: Step[] = [
  {
    id: "step-1",
    name: "Research Assistant",
    description: "A step that can research topics and gather information",
    type: "agent_step",
    system_message:
      "You are a helpful research assistant. Gather comprehensive information on given topics.",
    tools: ["web_search", "document_analysis"],
    model: "gpt-4o-mini",
  },
  {
    id: "step-2",
    name: "Data Analyst",
    description: "A step specialized in analyzing data and creating insights",
    type: "agent_step",
    system_message:
      "You are a data analyst. Analyze data and provide clear insights and visualizations.",
    tools: ["python_executor", "chart_generator"],
    model: "gpt-4o-mini",
  },
  {
    id: "step-3",
    name: "Content Writer",
    description: "A step that creates well-written content based on research",
    type: "agent_step",
    system_message:
      "You are a professional content writer. Create engaging, well-structured content.",
    tools: ["text_editor"],
    model: "gpt-4o-mini",
  },
  {
    id: "step-4",
    name: "Code Reviewer",
    description: "A step that reviews code for quality and best practices",
    type: "agent_step",
    system_message:
      "You are a senior software engineer. Review code for quality, security, and best practices.",
    tools: ["code_analysis", "security_scanner"],
    model: "gpt-4o-mini",
  },
  {
    id: "step-5",
    name: "Summary Step",
    description:
      "A step that takes outputs from other steps and generates comprehensive summaries",
    type: "agent_step",
    system_message:
      "You are a summary specialist. Take outputs from multiple steps and create clear, concise, and comprehensive summaries that highlight key findings, insights, and recommendations.",
    tools: ["text_processor", "content_aggregator"],
    model: "gpt-4o-mini",
  },
];

const mockStepLibrary: StepLibrary = {
  name: "Default Library",
  description: "A collection of default steps for AutoGen Studio",
  steps: mockSteps,
};

const mockWorkflows: Workflow[] = [
  {
    id: "workflow-1",
    name: "Research and Analysis Pipeline",
    description:
      "A workflow that researches a topic, analyzes data, creates content, and generates a summary",
    created_at: "2025-01-10T10:00:00Z",
    updated_at: "2025-01-10T10:00:00Z",
    config: {
      id: "workflow-1",
      name: "Research and Analysis Pipeline",
      description:
        "Sequential workflow for research, analysis, content creation, and summarization",
      steps: [mockSteps[0], mockSteps[1], mockSteps[2], mockSteps[4]],
      edges: [
        {
          id: "edge-1",
          from_step: "step-1",
          to_step: "step-2",
        },
        {
          id: "edge-2",
          from_step: "step-2",
          to_step: "step-3",
        },
        {
          id: "edge-3",
          from_step: "step-3",
          to_step: "step-5",
        },
      ],
      start_step_id: "step-1",
    } as WorkflowConfig,
  },
  {
    id: "workflow-2",
    name: "Code Generation and Review",
    description:
      "A workflow that generates code, reviews it, and prepares it for deployment",
    created_at: "2025-01-12T14:30:00Z",
    updated_at: "2025-01-12T14:30:00Z",
    config: {
      id: "workflow-2",
      name: "Code Generation and Review",
      description: "Generates and reviews code for quality assurance",
      steps: [mockSteps[2], mockSteps[3]],
      edges: [
        {
          id: "edge-4",
          from_step: "step-2",
          to_step: "step-3",
        },
      ],
      start_step_id: "step-2",
    } as WorkflowConfig,
  },
];

// Simulate API latency
const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export const workflowAPI = {
  getWorkflows: async (): Promise<ApiResponse<Workflow[]>> => {
    await sleep(500);
    console.log("API: getWorkflows", mockWorkflows);
    return { success: true, data: mockWorkflows };
  },

  getWorkflow: async (id: string): Promise<ApiResponse<Workflow>> => {
    await sleep(500);
    const workflow = mockWorkflows.find((w) => w.id === id);
    if (workflow) {
      console.log("API: getWorkflow", workflow);
      return { success: true, data: workflow };
    }
    return {
      success: false,
      data: {} as Workflow,
      message: "Workflow not found",
    };
  },

  getSteps: async (): Promise<ApiResponse<Step[]>> => {
    await sleep(300);
    console.log("API: getSteps", mockSteps);
    return { success: true, data: mockSteps };
  },

  getStepLibrary: async (): Promise<ApiResponse<StepLibrary>> => {
    await sleep(300);
    console.log("API: getStepLibrary", mockStepLibrary);
    return { success: true, data: mockStepLibrary };
  },

  createWorkflow: async (
    data: CreateWorkflowRequest
  ): Promise<ApiResponse<Workflow>> => {
    await sleep(500);
    const newWorkflow: Workflow = {
      id: `workflow-${Date.now()}`,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      ...data,
      config: {
        ...data.config,
        id: `config-${Date.now()}`,
      },
    };
    mockWorkflows.push(newWorkflow);
    console.log("API: createWorkflow", newWorkflow);
    return { success: true, data: newWorkflow };
  },

  updateWorkflow: async (
    id: string,
    data: UpdateWorkflowRequest
  ): Promise<ApiResponse<Workflow>> => {
    await sleep(500);
    const index = mockWorkflows.findIndex((w) => w.id === id);
    if (index !== -1) {
      const updatedWorkflow = {
        ...mockWorkflows[index],
        ...data,
        config: {
          ...mockWorkflows[index].config,
          ...data.config,
        },
        updated_at: new Date().toISOString(),
      };
      mockWorkflows[index] = updatedWorkflow;
      console.log("API: updateWorkflow", updatedWorkflow);
      return { success: true, data: updatedWorkflow };
    }
    return {
      success: false,
      data: {} as Workflow,
      message: "Workflow not found",
    };
  },

  deleteWorkflow: async (id: string): Promise<ApiResponse<boolean>> => {
    await sleep(500);
    const index = mockWorkflows.findIndex((w) => w.id === id);
    if (index !== -1) {
      mockWorkflows.splice(index, 1);
      console.log("API: deleteWorkflow", id);
      return { success: true, data: true };
    }
    return { success: false, data: false, message: "Workflow not found" };
  },

  runWorkflow: async (
    workflowId: string,
    input: Record<string, any>
  ): Promise<ApiResponse<WorkflowRun>> => {
    await sleep(1500);
    console.log("API: runWorkflow", workflowId, input);
    const run: WorkflowRun = {
      id: `run-${Date.now()}`,
      workflow_id: workflowId,
      status: "completed",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      inputs: input,
      outputs: [
        {
          step_id: "step-5",
          output: {
            summary: "This is a mock summary of the research and analysis.",
          },
        },
      ],
    };
    return { success: true, data: run };
  },
};
