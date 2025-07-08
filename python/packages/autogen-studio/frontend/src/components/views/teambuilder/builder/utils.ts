import { nanoid } from "nanoid";
import {
  TeamConfig,
  Component,
  ComponentConfig,
  AgentConfig,
} from "../../../types/datamodel";
import {
  isAssistantAgent,
  isUserProxyAgent,
  isWebSurferAgent,
  isStaticWorkbench,
  isMcpWorkbench,
} from "../../../types/guards";
import { CustomNode, CustomEdge } from "./types";

interface Position {
  x: number;
  y: number;
}

interface NodeDimensions {
  width: number;
  height: number;
}

// Updated layout configuration with dynamic height handling
const LAYOUT_CONFIG = {
  TEAM_NODE: {
    X_POSITION: 100,
    MIN_Y_POSITION: 200,
  },
  AGENT: {
    START_X: 600,
    START_Y: 200,
    X_STAGGER: 0,
    MIN_Y_STAGGER: 50, // Minimum vertical space between nodes
  },
  NODE: {
    WIDTH: 272,
    MIN_HEIGHT: 100,
    PADDING: 20,
  },
  // Estimated heights for different node contents
  CONTENT_HEIGHTS: {
    BASE: 80, // Header + basic info
    DESCRIPTION: 60,
    MODEL_SECTION: 100,
    TOOL_SECTION: 80,
    TOOL_ITEM: 40,
    AGENT_SECTION: 80,
    AGENT_ITEM: 40,
    TERMINATION_SECTION: 80,
  },
};

// Calculate estimated node height based on content
const calculateNodeHeight = (component: Component<ComponentConfig>): number => {
  let height = LAYOUT_CONFIG.CONTENT_HEIGHTS.BASE;

  // Add height for description if present
  if (component.description) {
    height += LAYOUT_CONFIG.CONTENT_HEIGHTS.DESCRIPTION;
  }

  // Add heights for specific component types
  switch (component.component_type) {
    case "team":
      const teamConfig = component as Component<TeamConfig>;
      // Add height for agents section
      if (teamConfig.config.participants?.length) {
        height += LAYOUT_CONFIG.CONTENT_HEIGHTS.AGENT_SECTION;
        height +=
          teamConfig.config.participants.length *
          LAYOUT_CONFIG.CONTENT_HEIGHTS.AGENT_ITEM;
      }
      // Add height for termination section if present
      if (teamConfig.config.termination_condition) {
        height += LAYOUT_CONFIG.CONTENT_HEIGHTS.TERMINATION_SECTION;
      }
      break;

    case "agent":
      // Only AssistantAgent has model_client and tools
      if (isAssistantAgent(component)) {
        height += 200;
        // Add height for workbench section if present
        const workbenchConfig = component.config.workbench;
        if (workbenchConfig) {
          // Handle both single workbench object and array of workbenches
          const workbenches = Array.isArray(workbenchConfig)
            ? workbenchConfig
            : [workbenchConfig];

          if (workbenches.length > 0) {
            // Add height for workbench section header
            height += LAYOUT_CONFIG.CONTENT_HEIGHTS.TOOL_SECTION;

            // Calculate total height for all workbenches
            workbenches.forEach((workbench) => {
              if (!workbench) return;

              if (isStaticWorkbench(workbench)) {
                // StaticWorkbench: count individual tools
                const toolCount = workbench.config.tools?.length || 0;
                if (toolCount > 0) {
                  height += toolCount * LAYOUT_CONFIG.CONTENT_HEIGHTS.TOOL_ITEM;
                }
              } else if (isMcpWorkbench(workbench)) {
                // MCP workbench: add standard height for dynamic tools display
                height += LAYOUT_CONFIG.CONTENT_HEIGHTS.TOOL_ITEM;
              }
            });
          }
        }
      }
      if (isWebSurferAgent(component)) {
        height += 100;
      }

      if (isUserProxyAgent(component)) {
        height += -100;
      }

      break;

    case "workbench":
      // Add height for workbench content
      if (isStaticWorkbench(component)) {
        // StaticWorkbench: show tools
        const toolCount = component.config.tools?.length || 0;
        height += LAYOUT_CONFIG.CONTENT_HEIGHTS.TOOL_SECTION;
        if (toolCount > 0) {
          height += toolCount * LAYOUT_CONFIG.CONTENT_HEIGHTS.TOOL_ITEM;
        }
      } else if (isMcpWorkbench(component)) {
        // MCP workbench: show server configuration
        height += LAYOUT_CONFIG.CONTENT_HEIGHTS.TOOL_SECTION;
        height += LAYOUT_CONFIG.CONTENT_HEIGHTS.TOOL_ITEM; // For server info display
      }
      break;
  }

  return Math.max(height, LAYOUT_CONFIG.NODE.MIN_HEIGHT);
};

// Calculate position for an agent node considering previous nodes' heights
const calculateAgentPosition = (
  index: number,
  previousNodes: CustomNode[]
): Position => {
  const previousNodeHeights = previousNodes.map(
    (node) => calculateNodeHeight(node.data.component) + 50
  );

  const totalPreviousHeight = previousNodeHeights.reduce(
    (sum, height) => sum + height + LAYOUT_CONFIG.AGENT.MIN_Y_STAGGER,
    0
  );

  return {
    x: LAYOUT_CONFIG.AGENT.START_X + index * LAYOUT_CONFIG.AGENT.X_STAGGER,
    y: LAYOUT_CONFIG.AGENT.START_Y + totalPreviousHeight,
  };
};

// Calculate team node position based on connected agents
const calculateTeamPosition = (agentNodes: CustomNode[]): Position => {
  if (agentNodes.length === 0) {
    return {
      x: LAYOUT_CONFIG.TEAM_NODE.X_POSITION,
      y: LAYOUT_CONFIG.TEAM_NODE.MIN_Y_POSITION,
    };
  }

  // Calculate the average Y position of all agent nodes
  const totalY = agentNodes.reduce((sum, node) => sum + node.position.y, 0);
  const averageY = totalY / agentNodes.length;

  // Ensure minimum Y position
  const y = Math.max(LAYOUT_CONFIG.TEAM_NODE.MIN_Y_POSITION, averageY);

  return {
    x: LAYOUT_CONFIG.TEAM_NODE.X_POSITION,
    y,
  };
};

// Helper to create nodes with consistent structure and dynamic height
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
    dimensions: {
      width: LAYOUT_CONFIG.NODE.WIDTH,
      height: calculateNodeHeight(component),
    },
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

// Convert team configuration to graph structure with dynamic layout
export const convertTeamConfigToGraph = (
  teamComponent: Component<TeamConfig>
): { nodes: CustomNode[]; edges: CustomEdge[] } => {
  const nodes: CustomNode[] = [];
  const edges: CustomEdge[] = [];

  // Create agent nodes first to calculate their positions
  const agentNodes: CustomNode[] = [];
  teamComponent.config.participants.forEach((participant, index) => {
    const position = calculateAgentPosition(index, agentNodes);
    const agentNode = createNode(position, participant);
    agentNodes.push(agentNode);
  });

  // Create team node with position based on agent positions
  const teamNode = createNode(calculateTeamPosition(agentNodes), teamComponent);

  // Add all nodes and create edges
  nodes.push(teamNode, ...agentNodes);
  agentNodes.forEach((agentNode) => {
    edges.push(createEdge(teamNode.id, agentNode.id, "agent-connection"));
  });

  return { nodes, edges };
};

// Layout existing nodes with dynamic heights
export const getLayoutedElements = (
  nodes: CustomNode[],
  edges: CustomEdge[]
): { nodes: CustomNode[]; edges: CustomEdge[] } => {
  // Find team node and agent nodes
  const teamNode = nodes.find((n) => n.data.type === "team");
  if (!teamNode) return { nodes, edges };

  const agentNodes = nodes.filter((n) => n.data.type !== "team");

  // Calculate new positions for agent nodes
  const layoutedAgentNodes = agentNodes.map((node, index) => ({
    ...node,
    position: calculateAgentPosition(index, agentNodes.slice(0, index)),
    data: {
      ...node.data,
      dimensions: {
        width: LAYOUT_CONFIG.NODE.WIDTH,
        height: calculateNodeHeight(node.data.component),
      },
    },
  }));

  // Update team node position
  const layoutedTeamNode = {
    ...teamNode,
    position: calculateTeamPosition(layoutedAgentNodes),
    data: {
      ...teamNode.data,
      dimensions: {
        width: LAYOUT_CONFIG.NODE.WIDTH,
        height: calculateNodeHeight(teamNode.data.component),
      },
    },
  };

  return {
    nodes: [layoutedTeamNode, ...layoutedAgentNodes],
    edges,
  };
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
