import {
  FoundryWorkflowConfig,
  WorkflowConfig,
  FoundryAgentConfig,
  Position,
  FoundryNodeData,
} from "./types";
import { Node, Edge } from "@xyflow/react";

// Type guard
export const isWorkflow = (
  config: FoundryWorkflowConfig
): config is WorkflowConfig => {
  return config.type === "workflow";
};

// Workflow utilities
export const createEmptyWorkflow = (
  name: string,
  description: string
): WorkflowConfig => ({
  id: `workflow-${Date.now()}`,
  name,
  description,
  type: "workflow",
  agents: [],
  edges: [],
  termination_conditions: ["max_messages:20"],
});

export const addAgentToWorkflow = (
  config: WorkflowConfig,
  agent: FoundryAgentConfig
): WorkflowConfig => {
  // Ensure no duplicate agents are added
  if (config.agents.some((a) => a.id === agent.id)) {
    return config;
  }
  return {
    ...config,
    agents: [...config.agents, agent],
  };
};

// Local storage keys
const getPositionKey = (workflowId: string) =>
  `workflow-${workflowId}-positions`;

// Save node positions to local storage
export const saveNodePosition = (
  workflowId: string,
  nodeId: string,
  position: { x: number; y: number }
) => {
  const key = getPositionKey(workflowId);
  const positions = JSON.parse(localStorage.getItem(key) || "{}");
  positions[nodeId] = position;
  localStorage.setItem(key, JSON.stringify(positions));
};

// Load node positions from local storage
export const loadNodePositions = (workflowId: string) => {
  const key = getPositionKey(workflowId);
  return JSON.parse(localStorage.getItem(key) || "{}");
};

// Remove a node's position from local storage
export const removeNodePosition = (workflowId: string, nodeId: string) => {
  const key = getPositionKey(workflowId);
  const positions = JSON.parse(localStorage.getItem(key) || "{}");
  delete positions[nodeId];
  localStorage.setItem(key, JSON.stringify(positions));
};

// Calculate a default position for a new node
export const calculateNodePosition = (index: number, totalNodes: number) => {
  const x = 250 * (index % 4);
  const y = 150 * Math.floor(index / 4);
  return { x, y };
};

// Convert workflow config to React Flow nodes
export const convertToReactFlowNodes = (
  config: WorkflowConfig,
  workflowId: string,
  onDelete: (id: string) => void
): Node<NodeData>[] => {
  const positions = loadNodePositions(workflowId);
  return config.steps.map((step, index): Node<NodeData> => {
    const position =
      positions[step.id] || calculateNodePosition(index, config.steps.length);
    return {
      id: step.id,
      type: "step",
      position,
      data: { step, onDelete },
    };
  });
};

// Convert workflow config to React Flow edges
export const convertToReactFlowEdges = (
  config: WorkflowConfig,
  edgeType: string
): Edge[] => {
  return config.edges.map((edge) => ({
    id: edge.id,
    source: edge.from_step,
    target: edge.to_step,
    type: edgeType,
  }));
};

// UI layout and color utilities
export const getWorkflowTypeColor = (type: "workflow") => {
  return "bg-blue-500/10 text-blue-500";
};

// Add a new step to the workflow config
export const addStepToWorkflow = (
  config: WorkflowConfig,
  step: Step
): WorkflowConfig => {
  // Avoid adding duplicate steps
  if (config.steps.some((s) => s.id === step.id)) {
    return config;
  }
  return {
    ...config,
    steps: [...config.steps, step],
  };
};
