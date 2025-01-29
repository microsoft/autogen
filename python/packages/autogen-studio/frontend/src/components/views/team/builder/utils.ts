import { nanoid } from "nanoid";
import {
  TeamConfig,
  Component,
  ComponentConfig,
} from "../../../types/datamodel";
import { CustomNode, CustomEdge } from "./types";

interface Position {
  x: number;
  y: number;
}

// Layout configuration
const LAYOUT_CONFIG = {
  TEAM_NODE: {
    X_POSITION: 100,
    MIN_Y_POSITION: 200,
  },
  AGENT: {
    START_X: 600, // Starting X position for first agent
    START_Y: 200, // Starting Y position for first agent
    X_STAGGER: 100, // X offset for each subsequent agent
    Y_STAGGER: 200, // Y offset for each subsequent agent
  },
  NODE: {
    WIDTH: 272,
    HEIGHT: 200,
  },
};

// Calculate staggered position for agents
const calculateAgentPosition = (
  index: number,
  totalAgents: number
): Position => {
  return {
    x: LAYOUT_CONFIG.AGENT.START_X + index * LAYOUT_CONFIG.AGENT.X_STAGGER,
    y: LAYOUT_CONFIG.AGENT.START_Y + index * LAYOUT_CONFIG.AGENT.Y_STAGGER,
  };
};

// Calculate team node position based on agent positions
const calculateTeamPosition = (totalAgents: number): Position => {
  const centerY = ((totalAgents - 1) * LAYOUT_CONFIG.AGENT.Y_STAGGER) / 2;
  return {
    x: LAYOUT_CONFIG.TEAM_NODE.X_POSITION,
    y: Math.max(
      LAYOUT_CONFIG.TEAM_NODE.MIN_Y_POSITION,
      LAYOUT_CONFIG.AGENT.START_Y + centerY
    ),
  };
};

// Helper to create nodes with consistent structure
const createNode = (
  position: Position,
  component: Component<ComponentConfig>,
  label?: string
): CustomNode => ({
  id: nanoid(),
  position,
  type: component.component_type,
  data: {
    label: label || component.label || component.component_type,
    component,
    type: component.component_type,
  },
});

// Helper to create edges with consistent structure
const createEdge = (
  source: string,
  target: string,
  type: "agent-connection"
): CustomEdge => ({
  id: `e${source}-${target}`,
  source,
  target,
  sourceHandle: `${source}-agent-output-handle`,
  targetHandle: `${target}-agent-input-handle`,
  type,
});

// Convert team configuration to graph structure
export const convertTeamConfigToGraph = (
  teamComponent: Component<TeamConfig>
): { nodes: CustomNode[]; edges: CustomEdge[] } => {
  const nodes: CustomNode[] = [];
  const edges: CustomEdge[] = [];
  const totalAgents = teamComponent.config.participants.length;

  // Create team node
  const teamNode = createNode(
    calculateTeamPosition(totalAgents),
    teamComponent
  );
  nodes.push(teamNode);

  // Create agent nodes with staggered layout
  teamComponent.config.participants.forEach((participant, index) => {
    const position = calculateAgentPosition(index, totalAgents);
    const agentNode = createNode(position, participant);
    nodes.push(agentNode);

    // Connect to team
    edges.push(createEdge(teamNode.id, agentNode.id, "agent-connection"));
  });

  return { nodes, edges };
};

// This is the function expected by the store
export const getLayoutedElements = (
  nodes: CustomNode[],
  edges: CustomEdge[]
): { nodes: CustomNode[]; edges: CustomEdge[] } => {
  // Find team node and count agents
  const teamNode = nodes.find((n) => n.data.type === "team");
  if (!teamNode) return { nodes, edges };

  // Count agent nodes
  const agentNodes = nodes.filter((n) => n.data.type !== "team");
  const totalAgents = agentNodes.length;

  // Calculate new positions
  const layoutedNodes = nodes.map((node) => {
    if (node.data.type === "team") {
      // Position team node
      return {
        ...node,
        position: calculateTeamPosition(totalAgents),
      };
    } else {
      // Position agent node
      const agentIndex = agentNodes.findIndex((n) => n.id === node.id);
      return {
        ...node,
        position: calculateAgentPosition(agentIndex, totalAgents),
      };
    }
  });

  return { nodes: layoutedNodes, edges };
};

// Generate unique names (unchanged)
export const getUniqueName = (
  baseName: string,
  existingNames: string[]
): string => {
  let validBaseName = baseName
    .replace(/[^a-zA-Z0-9_$]/g, "_")
    .replace(/^([^a-zA-Z_$])/, "_$1");

  if (!existingNames.includes(validBaseName)) return validBaseName;

  let counter = 1;
  while (existingNames.includes(`${validBaseName}_${counter}`)) {
    counter++;
  }
  return `${validBaseName}_${counter}`;
};
