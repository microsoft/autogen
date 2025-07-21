import { Component } from "../../types/datamodel";
import { WorkflowConfig, NodeData, StepConfig, StepExecution } from "./types";
import { Node, Edge } from "@xyflow/react";
import dagre from "@dagrejs/dagre";

// Workflow utilities
export const createEmptyWorkflow = (
  name: string,
  description: string
): WorkflowConfig => ({
  id: `workflow-${Date.now()}`,
  name,
  description,
  steps: [],
  edges: [],
});

// Local storage keys
const getPositionKey = (workflowId: number) =>
  `workflow-${workflowId}-positions`;

// Save node positions to local storage
export const saveNodePosition = (
  workflowId: number,
  nodeId: string,
  position: { x: number; y: number }
) => {
  const key = getPositionKey(workflowId);
  const positions = JSON.parse(localStorage.getItem(key) || "{}");
  positions[nodeId] = position;
  localStorage.setItem(key, JSON.stringify(positions));
};

// Load node positions from local storage
export const loadNodePositions = (workflowId: number) => {
  const key = getPositionKey(workflowId);
  return JSON.parse(localStorage.getItem(key) || "{}");
};

// Remove a node's position from local storage
export const removeNodePosition = (workflowId: number, nodeId: string) => {
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
  workflowId: number,
  onDelete: (id: string) => void,
  onStepClick?: (step: StepConfig, executionData?: StepExecution) => void
): Node<NodeData>[] => {
  const positions = loadNodePositions(workflowId);

  return (config.steps || []).map((step, index): Node<NodeData> => {
    const position =
      positions[step.config.step_id] ||
      calculateNodePosition(index, config.steps?.length || 0);
    return {
      id: step.config.step_id,
      type: "step",
      position,
      data: {
        step: step.config,
        onDelete,
        onStepClick,
        executionStatus: undefined, // Will be set by execution state
      },
    };
  });
};

// Convert workflow config to React Flow edges
export const convertToReactFlowEdges = (
  config: WorkflowConfig,
  edgeType: string
): Edge[] => {
  return (config.edges || []).map((edge) => ({
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
  step: Component<StepConfig>
): WorkflowConfig => {
  // Avoid adding duplicate steps
  if (config.steps?.some((s) => s.config.step_id === step.config.step_id)) {
    return config;
  }
  return {
    ...config,
    steps: [...config.steps, { ...step, config: step.config }],
  };
};

// Layout nodes using dagre (left-to-right)
export function getDagreLayoutedNodes(
  nodes: Node<NodeData>[],
  edges: Edge[],
  direction: "LR" | "TB" = "LR"
): Node<NodeData>[] {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: direction });

  // Set nodes with width/height (adjust as needed for your node size)
  nodes.forEach((node) => {
    g.setNode(node.id, { width: 220, height: 80 });
  });

  // Set edges
  edges.forEach((edge) => {
    g.setEdge(edge.source, edge.target);
  });

  dagre.layout(g);

  // Update node positions
  return nodes.map((node) => {
    const pos = g.node(node.id);
    if (!pos) return node;
    return {
      ...node,
      position: { x: pos.x - 110, y: pos.y - 40 }, // Center node
    };
  });
}
