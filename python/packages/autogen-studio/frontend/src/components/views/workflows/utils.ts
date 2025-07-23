import { Component } from "../../types/datamodel";
import { WorkflowConfig, NodeData, StepConfig, StepExecution, EdgeCondition } from "./types";
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
        workflowConfig: config, // Pass workflow config to determine start/end nodes
      },
    };
  });
};

// Format condition for display on edge label
export const formatConditionLabel = (condition?: EdgeCondition): string => {
  if (!condition || condition.type === "always") return "";
  
  if (condition.expression) {
    return `[${condition.expression}]`;
  }
  
  if (condition.field && condition.operator && condition.value !== undefined) {
    const valueStr = typeof condition.value === 'string' ? `"${condition.value}"` : String(condition.value);
    return `[${condition.field} ${condition.operator} ${valueStr}]`;
  }
  
  return `[${condition.type}]`;
};

// Get edge styling based on condition type (only style during execution)
export const getConditionalEdgeStyle = (condition?: EdgeCondition, isExecuting?: boolean) => {
  const baseStyle = {
    stroke: "#6b7280",
    strokeWidth: 2,
  };

  // Only apply conditional styling during execution
  if (!isExecuting || !condition || condition.type === "always") {
    return baseStyle;
  }
  
  // Conditional edges get dashed lines and different colors during execution
  const conditionalStyle = {
    strokeWidth: 2,
    strokeDasharray: "5,5",
  };
  
  switch (condition.type) {
    case "output_based":
      return {
        ...conditionalStyle,
        stroke: "#3b82f6", // Blue for output-based
      };
    case "state_based":
      return {
        ...conditionalStyle,
        stroke: "#8b5cf6", // Purple for state-based
      };
    default:
      return {
        ...conditionalStyle,
        stroke: "#6b7280",
      };
  }
};

// Convert workflow config to React Flow edges
export const convertToReactFlowEdges = (
  config: WorkflowConfig,
  edgeType: string,
  isExecuting?: boolean
): Edge[] => {
  return (config.edges || []).map((edge) => {
    const label = formatConditionLabel(edge.condition);
    const style = getConditionalEdgeStyle(edge.condition, isExecuting);
    
    return {
      id: edge.id,
      source: edge.from_step,
      target: edge.to_step,
      type: edgeType,
      label: label || undefined,
      style,
      data: {
        condition: edge.condition,
      },
    };
  });
};

// UI layout and color utilities
export const getWorkflowTypeColor = (type: "workflow") => {
  return "bg-blue-500/10 text-blue-500";
};

// Get condition type color for UI elements
export const getConditionTypeColor = (condition?: EdgeCondition) => {
  if (!condition || condition.type === "always") {
    return "text-gray-600";
  }
  
  switch (condition.type) {
    case "output_based":
      return "text-blue-600";
    case "state_based":
      return "text-purple-600";
    default:
      return "text-gray-600";
  }
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
