import { Component, DBModel } from "../../types/datamodel";

// ========== Execution Status Enums ==========
export enum StepStatus {
  PENDING = "pending",
  RUNNING = "running",
  COMPLETED = "completed",
  FAILED = "failed",
  SKIPPED = "skipped",
  CANCELLED = "cancelled",
}

export enum WorkflowStatus {
  CREATED = "created",
  RUNNING = "running",
  COMPLETED = "completed",
  FAILED = "failed",
  CANCELLED = "cancelled",
}

// ========== Workflow Event Types ==========
export enum WorkflowEventType {
  WORKFLOW_STARTED = "workflow_started",
  WORKFLOW_COMPLETED = "workflow_completed",
  WORKFLOW_FAILED = "workflow_failed",
  WORKFLOW_CANCELLED = "workflow_cancelled",
  STEP_STARTED = "step_started",
  STEP_COMPLETED = "step_completed",
  STEP_FAILED = "step_failed",
  EDGE_ACTIVATED = "edge_activated",
}

// Base workflow event
export interface WorkflowEvent {
  event_type: WorkflowEventType;
  timestamp: string; // ISO datetime string
  workflow_id: string;
  run_id?: string; // Added for WebSocket context
}

export interface WorkflowStartedEvent extends WorkflowEvent {
  event_type: WorkflowEventType.WORKFLOW_STARTED;
  initial_input: Record<string, any>;
}

export interface WorkflowCompletedEvent extends WorkflowEvent {
  event_type: WorkflowEventType.WORKFLOW_COMPLETED;
  execution: WorkflowExecution;
}

export interface WorkflowFailedEvent extends WorkflowEvent {
  event_type: WorkflowEventType.WORKFLOW_FAILED;
  error: string;
  execution?: WorkflowExecution;
}

export interface WorkflowCancelledEvent extends WorkflowEvent {
  event_type: WorkflowEventType.WORKFLOW_CANCELLED;
  execution: WorkflowExecution;
  reason: string;
}

export interface StepStartedEvent extends WorkflowEvent {
  event_type: WorkflowEventType.STEP_STARTED;
  step_id: string;
  input_data: Record<string, any>;
}

export interface StepCompletedEvent extends WorkflowEvent {
  event_type: WorkflowEventType.STEP_COMPLETED;
  step_id: string;
  output_data: Record<string, any>;
  duration_seconds: number;
}

export interface StepFailedEvent extends WorkflowEvent {
  event_type: WorkflowEventType.STEP_FAILED;
  step_id: string;
  error: string;
  duration_seconds: number;
}

export interface EdgeActivatedEvent extends WorkflowEvent {
  event_type: WorkflowEventType.EDGE_ACTIVATED;
  from_step: string;
  to_step: string;
  data: Record<string, any>;
}

// Union type for all possible events
export type WorkflowEventUnion =
  | WorkflowStartedEvent
  | WorkflowCompletedEvent
  | WorkflowFailedEvent
  | WorkflowCancelledEvent
  | StepStartedEvent
  | StepCompletedEvent
  | StepFailedEvent
  | EdgeActivatedEvent;

// ========== Execution Tracking Types ==========
export interface StepExecution {
  step_id: string;
  status: StepStatus;
  start_time?: string; // ISO datetime string
  end_time?: string;
  input_data?: Record<string, any>;
  output_data?: Record<string, any>;
  error?: string;
  retry_count: number;
}

export interface WorkflowExecution {
  id: string;
  workflow_id: string;
  status: WorkflowStatus;
  start_time?: string; // ISO datetime string
  end_time?: string;
  state: Record<string, any>;
  step_executions: Record<string, StepExecution>;
  error?: string;
}

// ========== Core Workflow Types ==========

// {
//     "provider": "autogenstudio.workflow.steps.EchoStep",
//     "component_type": "step",
//     "version": 1,
//     "component_version": 1,
//     "description": "A simple step that echoes input with prefix/suffix - fully serializable.",
//     "label": "EchoStep",
//     "config": {
//         "step_id": "receive",
//         "metadata": {
//             "name": "Receive Message",
//             "tags": [],
//             "max_retries": 0
//         },
//         "input_type_name": "MessageInput",
//         "output_type_name": "MessageOutput",
//         "input_schema": {
//             "properties": {
//                 "message": {
//                     "title": "Message",
//                     "type": "string"
//                 }
//             },
//             "required": [
//                 "message"
//             ],
//             "title": "MessageInput",
//             "type": "object"
//         },
//         "output_schema": {
//             "properties": {
//                 "result": {
//                     "title": "Result",
//                     "type": "string"
//                 }
//             },
//             "required": [
//                 "result"
//             ],
//             "title": "MessageOutput",
//             "type": "object"
//         },
//         "prefix": "📥 RECEIVED: ",
//         "suffix": " [INBOX]"
//     }
// }

// A Step in a workflow. For now, it retains agent-like properties for the UI.
// Matches backend step config structure
export interface StepConfig {
  step_id: string;
  metadata: {
    name: string;
    description?: string;
    tags?: string[];
    max_retries?: number;
    timeout_seconds?: number;
    [key: string]: any;
  };
  input_type_name: string;
  output_type_name: string;
  input_schema: Record<string, any>;
  output_schema: Record<string, any>;
  prefix?: string;
  suffix?: string;
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
  steps: Component<StepConfig>[];
  edges: WorkflowEdge[];
  start_step_id?: string;
  end_step_ids?: string[];
  initial_state?: Record<string, any>;
  metadata?: Record<string, any>;
}

// The top-level workflow object, containing the config and other metadata.
export interface Workflow extends DBModel {
  config: Component<WorkflowConfig>;
}

// UI State Types
export interface WorkflowState {
  currentWorkflow: Workflow | null;
  workflows: Workflow[];
  selectedStep: StepConfig | null;
  isEditing: boolean;
  isLoading: boolean;
  error: string | null;
}

// Data structure for nodes in React Flow
export interface NodeData extends Record<string, unknown> {
  step: StepConfig;
  onDelete?: (id: string) => void;
  executionStatus?: StepStatus;
  executionData?: StepExecution;
  onStepClick?: (step: StepConfig, executionData?: StepExecution) => void;
  // any other node-specific data
}

// A library of reusable steps
export interface StepLibrary {
  name: string;
  description: string;
  steps: StepConfig[];
}

// ========== Backend API Response Types ==========
export interface ApiResponse<T> {
  status: boolean; // Matches backend response format
  data: T;
  message?: string;
}

// Backend workflow database model
export interface WorkflowDB {
  id: number;
  name: string;
  description: string;
  config: Record<string, any>;
  tags: string[];
  user_id: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// Backend API request types matching workflows.py
export interface CreateWorkflowBackendRequest {
  name: string;
  description: string;
  config: Record<string, any>;
  tags: string[];
  user_id: string;
}

export interface UpdateWorkflowBackendRequest {
  name?: string;
  description?: string;
  config?: Record<string, any>;
  tags?: string[];
  is_active?: boolean;
}

export interface CreateWorkflowRunRequest {
  workflow_id?: number;
  workflow_config?: Record<string, any>;
}

export interface WorkflowRunResponse {
  status: boolean;
  data: {
    run_id: string;
    workflow_config: Record<string, any>;
  };
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
