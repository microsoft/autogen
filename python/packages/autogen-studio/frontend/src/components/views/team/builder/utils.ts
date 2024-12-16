import dagre from "@dagrejs/dagre";
import { CustomNode, CustomEdge } from "./types";
import { nanoid } from "nanoid";
import {
  TeamConfig,
  ModelConfig,
  AgentConfig,
  ToolConfig,
  ComponentTypes,
  TerminationConfig,
} from "../../../types/datamodel";

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
  const teamNode = createNode(
    "team",
    { x: 400, y: 50 },
    {
      ...config,
      // participants: [], // Clear participants as we'll rebuild from edges
    }
  );
  nodes.push(teamNode);

  // Add model client if present
  if (config.team_type === "SelectorGroupChat" && config.model_client) {
    const modelNode = createNode(
      "model",
      { x: 200, y: 50 },
      config.model_client,
      config.model_client.model
    );
    nodes.push(modelNode);
    edges.push({
      id: nanoid(),
      source: modelNode.id,
      target: teamNode.id,
      sourceHandle: `${modelNode.id}-model-output-handle`,
      targetHandle: `${teamNode.id}-model-input-handle`,
      type: "model-connection",
    });
  }

  // Add participants (agents)
  config.participants.forEach((participant, index) => {
    const position = calculateParticipantPosition(
      index,
      config.participants.length
    );
    const agentNode = createNode("agent", position, {
      ...participant,
      // tools: [], // Clear tools as we'll rebuild from edges
    });
    nodes.push(agentNode);

    // Connect to team
    edges.push({
      id: nanoid(),
      source: teamNode.id,
      target: agentNode.id,
      sourceHandle: `${teamNode.id}-agent-output-handle`,
      targetHandle: `${agentNode.id}-agent-input-handle`,
      type: "agent-connection",
    });

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
      edges.push({
        id: nanoid(),
        source: agentModelNode.id,
        target: agentNode.id,
        sourceHandle: `${agentModelNode.id}-model-output-handle`,
        targetHandle: `${agentNode.id}-model-input-handle`,
        type: "model-connection",
      });
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
      edges.push({
        id: nanoid(),
        source: toolNode.id,
        target: agentNode.id,
        sourceHandle: `${toolNode.id}-tool-output-handle`,
        targetHandle: `${agentNode.id}-tool-input-handle`,
        type: "tool-connection",
      });
    });
  });

  // Add termination condition if present
  if (config?.termination_condition) {
    const terminationNode = createNode(
      "termination",
      { x: 600, y: 50 },
      config.termination_condition
    );
    nodes.push(terminationNode);
    edges.push({
      id: nanoid(),
      source: terminationNode.id,
      target: teamNode.id,
      sourceHandle: `${terminationNode.id}-termination-output-handle`,
      targetHandle: `${teamNode.id}-termination-input-handle`,
      type: "termination-connection",
    });
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
  const calculateRank = (node: CustomNode) => {
    if (node.data.type === "model") {
      // Check if this model is connected to a team or agent
      const isTeamModel = edges.some(
        (e) =>
          e.source === node.id &&
          nodes.find((n) => n.id === e.target)?.data.type === "team"
      );
      return isTeamModel ? 0 : 2;
    }

    switch (node.data.type) {
      case "team":
        return 1;
      case "agent":
        return 3;
      case "tool":
        return 4;
      case "termination":
        return 1; // Same rank as team
      default:
        return 0;
    }
  };

  g.setGraph({
    rankdir: "LR",
    nodesep: 250,
    ranksep: 150,
    ranker: "network-simplex", // or "tight-tree" depending on needs
    align: "DL",
  });
  g.setDefaultEdgeLabel(() => ({}));

  // Add nodes to the graph with their dimensions
  nodes.forEach((node) => {
    const rank = calculateRank(node);
    g.setNode(node.id, {
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
      rank,
    });
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

export const getNodeConnections = (nodeId: string, edges: CustomEdge[]) => {
  return {
    modelClient:
      edges.find((e) => e.target === nodeId && e.type === "model-connection")
        ?.source || null,

    tools: edges
      .filter((e) => e.target === nodeId && e.type === "tool-connection")
      .map((e) => e.source),

    participants: edges
      .filter((e) => e.source === nodeId && e.type === "agent-connection")
      .map((e) => e.target),
  };
};
