import dagre from "@dagrejs/dagre";
import { CustomNode, CustomEdge } from "../types";
import { nanoid } from "nanoid";
import {
  TeamConfig,
  ModelConfig,
  AgentConfig,
  ToolConfig,
  ComponentTypes,
  TerminationConfig,
} from "../../../../../types/datamodel";

interface ConversionResult {
  nodes: CustomNode[];
  edges: CustomEdge[];
}

interface Position {
  x: number;
  y: number;
}

// Calculate positions for participants in a grid layout
const calculateParticipantPosition = (
  index: number,
  totalParticipants: number
): Position => {
  const GRID_SPACING = 250;
  const PARTICIPANTS_PER_ROW = 3;

  const row = Math.floor(index / PARTICIPANTS_PER_ROW);
  const col = index % PARTICIPANTS_PER_ROW;

  return {
    x: col * GRID_SPACING,
    y: (row + 1) * GRID_SPACING,
  };
};

// Helper to create nodes with consistent structure
const createNode = (
  type: ComponentTypes,
  position: Position,
  config:
    | TeamConfig
    | ModelConfig
    | AgentConfig
    | ToolConfig
    | TerminationConfig,
  label?: string
): CustomNode => ({
  id: nanoid(),
  type,
  position,
  data: {
    label: label || type,
    type,
    config,
    connections: {
      modelClient: null,
      tools: [],
      participants: [],
      termination: null,
    },
  },
});

// Helper to create edges with consistent structure
const createEdge = (
  source: string,
  target: string,
  type:
    | "model-connection"
    | "tool-connection"
    | "agent-connection"
    | "team-connection"
    | "termination-connection"
): CustomEdge => ({
  id: `e${source}-${target}`,
  source,
  target,
  type,
});

export const convertTeamConfigToGraph = (
  config: TeamConfig
): ConversionResult => {
  const nodes: CustomNode[] = [];
  const edges: CustomEdge[] = [];

  // Create team node
  const teamNode = createNode("team", { x: 400, y: 50 }, config);
  nodes.push(teamNode);

  // Add model client if present
  if (config.model_client) {
    const modelNode = createNode(
      "model",
      { x: 200, y: 50 },
      config.model_client,
      config.model_client.model
    );
    nodes.push(modelNode);
    edges.push(createEdge(modelNode.id, teamNode.id, "model-connection"));
  }

  // Add participants (agents)
  config.participants.forEach((participant, index) => {
    const position = calculateParticipantPosition(
      index,
      config.participants.length
    );
    const agentNode = createNode("agent", position, participant);
    nodes.push(agentNode);

    // Connect to team
    edges.push(createEdge(teamNode.id, agentNode.id, "agent-connection"));

    // Add agent's model client if present
    if (participant.model_client) {
      const agentModelNode = createNode(
        "model",
        {
          x: position.x - 150,
          y: position.y,
        },
        participant.model_client,
        participant.model_client.model
      );
      nodes.push(agentModelNode);
      edges.push(
        createEdge(agentModelNode.id, agentNode.id, "model-connection")
      );
    }

    // Add agent's tools
    participant.tools?.forEach((tool, toolIndex) => {
      const toolNode = createNode(
        "tool",
        {
          x: position.x + 150,
          y: position.y + toolIndex * 100,
        },
        tool
      );
      nodes.push(toolNode);
      edges.push(createEdge(toolNode.id, agentNode.id, "tool-connection"));
    });
  });

  if (config?.termination_condition) {
    const terminationNode = createNode(
      "termination",
      { x: 600, y: 50 }, // Adjust position as needed
      config.termination_condition
    );
    nodes.push(terminationNode);
    edges.push(
      createEdge(terminationNode.id, teamNode.id, "termination-connection")
    );
  }

  return { nodes, edges };
};

const NODE_WIDTH = 272;
const NODE_HEIGHT = 200;

export const getLayoutedElements = (
  nodes: CustomNode[],
  edges: CustomEdge[]
) => {
  const g = new dagre.graphlib.Graph();
  g.setGraph({
    rankdir: "LR", // Left to right layout
    nodesep: 200, // Vertical spacing between nodes
    ranksep: 200, // Horizontal spacing between nodes
    align: "DL", // Down-left alignment
  });
  g.setDefaultEdgeLabel(() => ({}));

  // Add nodes to the graph with their dimensions
  nodes.forEach((node) => {
    g.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });

  // Add edges to the graph
  edges.forEach((edge) => {
    g.setEdge(edge.source, edge.target);
  });

  // Apply the layout
  dagre.layout(g);

  // Get the laid out nodes with their new positions
  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = g.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - NODE_WIDTH / 2,
        y: nodeWithPosition.y - NODE_HEIGHT / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};
