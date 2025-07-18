// A Step in a workflow. For now, it retains agent-like properties for the UI.
export interface Step {
  id: string;
  name: string;
  description: string;
  type: "agent_step"; // A more generic type
  system_message?: string;
  tools?: string[];
  model?: string;
  metadata?: Record<string, any>;
}

// An Edge in the workflow graph, connecting two steps.
export interface WorkflowEdge {
  id: string;
  from_step: string; // Source step id
  to_step: string; // Target step id
  condition?: string; // Optional condition for the edge
}

// The configuration for a workflow, mirroring the backend spec.
export interface WorkflowConfig {
  id: string;
  name: string;
  description: string;
  steps: Step[];
  edges: WorkflowEdge[];
  start_step_id?: string;
  end_step_ids?: string[];
  initial_state?: Record<string, any>;
  metadata?: Record<string, any>;
}

// The top-level workflow object, containing the config and other metadata.
export interface Workflow {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
  config: WorkflowConfig;
  user_id?: string;
}

// UI State Types
export interface WorkflowState {
  currentWorkflow: Workflow | null;
  workflows: Workflow[];
  selectedStep: Step | null;
  isEditing: boolean;
  isLoading: boolean;
  error: string | null;
}

// Data structure for nodes in React Flow
export interface NodeData extends Record<string, unknown> {
  step: Step;
  onDelete?: (id: string) => void;
  // any other node-specific data
}

// A library of reusable steps
export interface StepLibrary {
  name: string;
  description: string;
  steps: Step[];
}

// API Response Types
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string; // Optional error message
}

// API Request Payloads
export interface CreateWorkflowRequest {
  name: string;
  description: string;
  config: WorkflowConfig;
}

export interface UpdateWorkflowRequest {
  id: string;
  name?: string;
  description?: string;
  config?: Partial<WorkflowConfig>;
}
