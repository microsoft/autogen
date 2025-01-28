import dagre from "@dagrejs/dagre";
import { CustomNode, CustomEdge, EdgeTypes } from "./types";
import { nanoid } from "nanoid";
import {
  TeamConfig,
  Component,
  ComponentConfig,
} from "../../../types/datamodel";
import { isAssistantAgent, isSelectorTeam } from "../../../types/guards";

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
  },
});

// Helper to create edges with consistent structure
const createEdge = (
  source: string,
  target: string,
  type: EdgeTypes
): CustomEdge => ({
  id: `e${source}-${target}`,
  source,
  target,
  type,
});

export const convertTeamConfigToGraph = (
  teamComponent: Component<TeamConfig>
): ConversionResult => {
  const nodes: CustomNode[] = [];
  const edges: CustomEdge[] = [];

  // Create team node
  const teamNode = createNode({ x: 400, y: 50 }, teamComponent);
  nodes.push(teamNode);

  // Add model client if present
  if (isSelectorTeam(teamComponent) && teamComponent.config.model_client) {
    const modelNode = createNode(
      { x: 200, y: 50 },
      teamComponent.config.model_client,
      teamComponent.config.model_client.config.model
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
  teamComponent.config.participants.forEach((participant, index) => {
    const position = calculateParticipantPosition(
      index,
      teamComponent.config.participants.length
    );
    const agentNode = createNode(position, participant);
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
    if (isAssistantAgent(participant) && participant.config.model_client) {
      const agentModelNode = createNode(
        {
          x: position.x - 150,
          y: position.y,
        },
        participant.config.model_client,
        participant.config.model_client.config.model
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
    if (isAssistantAgent(participant) && participant.config.tools) {
      participant.config.tools.forEach((tool, toolIndex) => {
        const toolNode = createNode(
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
    }
  });

  // Add termination condition if present
  if (teamComponent.config.termination_condition) {
    const terminationNode = createNode(
      { x: 600, y: 50 },
      teamComponent.config.termination_condition
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

// Rest of the file remains the same since it deals with layout calculations
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

export const getUniqueName = (
  baseName: string,
  existingNames: string[]
): string => {
  // Convert baseName to valid identifier format
  let validBaseName = baseName
    // Replace spaces and special characters with underscore
    .replace(/[^a-zA-Z0-9_$]/g, "_")
    // Ensure it starts with a letter, underscore, or dollar sign
    .replace(/^([^a-zA-Z_$])/, "_$1");

  if (!existingNames.includes(validBaseName)) return validBaseName;

  let counter = 1;
  while (existingNames.includes(`${validBaseName}_${counter}`)) {
    counter++;
  }
  return `${validBaseName}_${counter}`;
};
