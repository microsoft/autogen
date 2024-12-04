import { create } from "zustand";
import { TeamBuilderState, CustomNode, CustomEdge, Position } from "./types";
import { nanoid } from "nanoid";
import {
  TeamConfig,
  AgentConfig,
  ModelConfig,
  ToolConfig,
  ComponentTypes,
  ComponentConfigTypes,
  TerminationConfig,
} from "../../../../types/datamodel";
import {
  convertTeamConfigToGraph,
  getLayoutedElements,
} from "./utils/converter";

const MAX_HISTORY = 50;

const isTeamConfig = (config: any): config is TeamConfig => {
  return "team_type" in config;
};

const isAgentConfig = (config: any): config is AgentConfig => {
  return "agent_type" in config;
};

const isModelConfig = (config: any): config is ModelConfig => {
  return "model_type" in config;
};

const isToolConfig = (config: any): config is ToolConfig => {
  return "tool_type" in config;
};

const isTerminationConfig = (config: any): config is TerminationConfig => {
  return "termination_type" in config;
};

const buildTeamConfig = (
  teamNode: CustomNode,
  nodes: CustomNode[],
  edges: CustomEdge[]
): TeamConfig | null => {
  if (!isTeamConfig(teamNode.data.config)) return null;

  const config = { ...teamNode.data.config };

  // Find connected model
  const modelEdge = edges.find(
    (e) => e.target === teamNode.id && e.type === "model-connection"
  );
  if (modelEdge) {
    const modelNode = nodes.find((n) => n.id === modelEdge.source);
    if (modelNode && isModelConfig(modelNode.data.config)) {
      config.model_client = modelNode.data.config;
    }
  }

  // Find participants
  config.participants = teamNode.data.connections.participants
    .map((participantId) => {
      const agentNode = nodes.find((n) => n.id === participantId);
      if (!agentNode || !isAgentConfig(agentNode.data.config)) return null;

      const agentConfig = { ...agentNode.data.config };

      // Get agent's model
      if (agentNode.data.connections.modelClient) {
        const modelNode = nodes.find(
          (n) => n.id === agentNode.data.connections.modelClient
        );
        if (modelNode && isModelConfig(modelNode.data.config)) {
          agentConfig.model_client = modelNode.data.config;
        }
      }

      // Get agent's tools
      agentConfig.tools = agentNode.data.connections.tools
        .map((toolId) => {
          const toolNode = nodes.find((n) => n.id === toolId);
          return toolNode?.data.config as ToolConfig;
        })
        .filter((tool): tool is ToolConfig => tool !== null);

      return agentConfig;
    })
    .filter((agent): agent is AgentConfig => agent !== null);

  return config;
};

export const useTeamBuilderStore = create<TeamBuilderState>((set, get) => ({
  nodes: [],
  edges: [],
  selectedNodeId: null,
  history: [],
  currentHistoryIndex: -1,
  originalConfig: null,

  addNode: (
    type: ComponentTypes,
    position: Position,
    config: ComponentConfigTypes,
    targetNodeId?: string
  ) => {
    let label = "";
    if (isTeamConfig(config)) {
      label = config.name || "Team";
    } else if (isAgentConfig(config)) {
      label = config.name || "Agent";
    } else if (isModelConfig(config)) {
      label = config.model || "Model";
    } else if (isToolConfig(config)) {
      label = config.name || "Tool";
    } else if (isTerminationConfig(config)) {
      label = config.termination_type || "Termination";
    }

    set((state) => {
      const newNode: CustomNode = {
        id: nanoid(),
        type,
        position,
        data: {
          label: label || "Node",
          type,
          config,
          connections: {
            modelClient: null,
            tools: [],
            participants: [],
          },
        },
      };

      let newNodes = [...state.nodes, newNode];
      let newEdges = [...state.edges];

      if (targetNodeId) {
        const targetNode = state.nodes.find((n) => n.id === targetNodeId);

        if (targetNode) {
          if (
            type === "model" &&
            ["team", "agent"].includes(targetNode.data.type)
          ) {
            // Get old model node id if it exists
            const oldModelId = targetNode.data.connections.modelClient;

            // Remove old model node and edge if they exist
            if (oldModelId) {
              newNodes = newNodes.filter((node) => node.id !== oldModelId);
              newEdges = newEdges.filter(
                (edge) =>
                  !(edge.source === oldModelId || edge.target === oldModelId)
              );
            }

            // Update target's model connection
            targetNode.data.connections.modelClient = newNode.id;
            if (isTeamConfig(targetNode.data.config) && isModelConfig(config)) {
              targetNode.data.config.model_client = config;
            } else if (
              isAgentConfig(targetNode.data.config) &&
              isModelConfig(config)
            ) {
              targetNode.data.config.model_client = config;
            }

            // Add new edge
            newEdges.push({
              id: nanoid(),
              source: newNode.id,
              target: targetNode.id,
              sourceHandle: `${newNode.id}-output-handle`,
              targetHandle: `${targetNode.id}-input-handle`,
              type: "model-connection",
            });
          } else if (type === "tool" && targetNode.data.type === "agent") {
            // Add tool connection
            const toolIndex = targetNode.data.connections.tools.length;
            targetNode.data.connections.tools.push(newNode.id);
            newEdges.push({
              id: nanoid(),
              source: newNode.id,
              target: targetNode.id,
              sourceHandle: `${newNode.id}-output-handle`,
              targetHandle: `${targetNode.id}-input-handle`,
              type: "tool-connection",
            });

            if (
              isAgentConfig(targetNode.data.config) &&
              isToolConfig(config) &&
              targetNode.data.config.tools
            ) {
              targetNode.data.config.tools.push(config);
            }
          } else if (type === "agent" && targetNode.data.type === "team") {
            if (isTeamConfig(targetNode.data.config)) {
              // Add participant connection
              targetNode.data.connections.participants.push(newNode.id);
              if (isAgentConfig(config)) {
                targetNode.data.config.participants.push(config);
              }

              newEdges.push({
                id: nanoid(),
                source: targetNode.id,
                target: newNode.id,
                sourceHandle: `${targetNode.id}-output-handle`,
                targetHandle: `${newNode.id}-output-handle`,
                type: "participant-connection",
              });
            }
          } else if (
            type === "termination" &&
            targetNode.data.type === "team"
          ) {
            // Add this block
            // Add termination connection
            if (isTeamConfig(targetNode.data.config)) {
              // Remove any existing termination condition
              if (targetNode.data.config.termination_condition) {
                const oldTerminationNodes = state.nodes.filter(
                  (n) => n.data.type === "termination"
                );
                newNodes = newNodes.filter(
                  (n) => !oldTerminationNodes.includes(n)
                );
              }

              // Update the team's termination condition
              targetNode.data.config.termination_condition =
                config as TerminationConfig;

              // Add new edge
              newEdges.push({
                id: nanoid(),
                source: newNode.id,
                target: targetNode.id,
                sourceHandle: `${newNode.id}-output-handle`,
                targetHandle: `${targetNode.id}-input-handle`,
                type: "termination-connection",
              });
            }
          }
        }
      }

      return {
        nodes: newNodes,
        edges: newEdges,
        history: [
          ...state.history.slice(0, state.currentHistoryIndex + 1),
          { nodes: newNodes, edges: newEdges },
        ].slice(-MAX_HISTORY),
        currentHistoryIndex: state.currentHistoryIndex + 1,
      };
    });
  },

  updateNode: (nodeId: string, updates: Partial<ComponentConfigTypes>) => {
    set((state) => {
      const newNodes = state.nodes.map((node) =>
        node.id === nodeId
          ? {
              ...node,
              data: {
                ...node.data,
                config: { ...node.data.config, ...updates },
              },
            }
          : node
      );

      return {
        nodes: newNodes,
        history: [
          ...state.history.slice(0, state.currentHistoryIndex + 1),
          { nodes: newNodes, edges: state.edges },
        ].slice(-MAX_HISTORY),
        currentHistoryIndex: state.currentHistoryIndex + 1,
      };
    });
  },

  removeNode: (nodeId: string) => {
    set((state) => {
      const newNodes = state.nodes.filter((node) => node.id !== nodeId);
      const newEdges = state.edges.filter(
        (edge) => edge.source !== nodeId && edge.target !== nodeId
      );

      return {
        nodes: newNodes,
        edges: newEdges,
        history: [
          ...state.history.slice(0, state.currentHistoryIndex + 1),
          { nodes: newNodes, edges: newEdges },
        ].slice(-MAX_HISTORY),
        currentHistoryIndex: state.currentHistoryIndex + 1,
      };
    });
  },

  addEdge: (edge: CustomEdge) => {
    set((state) => {
      let newEdges = [...state.edges];

      if (edge.type === "model-connection") {
        newEdges = newEdges.filter(
          (e) => !(e.target === edge.target && e.type === "model-connection")
        );
      }

      newEdges.push(edge);

      return {
        edges: newEdges,
        history: [
          ...state.history.slice(0, state.currentHistoryIndex + 1),
          { nodes: state.nodes, edges: newEdges },
        ].slice(-MAX_HISTORY),
        currentHistoryIndex: state.currentHistoryIndex + 1,
      };
    });
  },

  removeEdge: (edgeId: string) => {
    set((state) => {
      const newEdges = state.edges.filter((edge) => edge.id !== edgeId);

      return {
        edges: newEdges,
        history: [
          ...state.history.slice(0, state.currentHistoryIndex + 1),
          { nodes: state.nodes, edges: newEdges },
        ].slice(-MAX_HISTORY),
        currentHistoryIndex: state.currentHistoryIndex + 1,
      };
    });
  },

  setSelectedNode: (nodeId: string | null) => {
    set({ selectedNodeId: nodeId });
  },

  undo: () => {
    set((state) => {
      if (state.currentHistoryIndex <= 0) return state;

      const previousState = state.history[state.currentHistoryIndex - 1];
      return {
        ...state,
        nodes: previousState.nodes,
        edges: previousState.edges,
        currentHistoryIndex: state.currentHistoryIndex - 1,
      };
    });
  },

  redo: () => {
    set((state) => {
      if (state.currentHistoryIndex >= state.history.length - 1) return state;

      const nextState = state.history[state.currentHistoryIndex + 1];
      return {
        ...state,
        nodes: nextState.nodes,
        edges: nextState.edges,
        currentHistoryIndex: state.currentHistoryIndex + 1,
      };
    });
  },

  syncToJson: () => {
    const state = get();
    const teamNodes = state.nodes.filter((node) => node.data.type === "team");
    if (teamNodes.length === 0) return null;

    const teamNode = teamNodes[0];
    return buildTeamConfig(teamNode, state.nodes, state.edges);
  },

  layoutNodes: () => {
    const { nodes, edges } = get();
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      nodes,
      edges
    );

    set({
      nodes: layoutedNodes,
      edges: layoutedEdges,
      history: [
        ...get().history.slice(0, get().currentHistoryIndex + 1),
        { nodes: layoutedNodes, edges: layoutedEdges },
      ].slice(-MAX_HISTORY),
      currentHistoryIndex: get().currentHistoryIndex + 1,
    });
  },

  loadFromJson: (config: TeamConfig) => {
    const { nodes, edges } = convertTeamConfigToGraph(config);
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      nodes,
      edges
    );

    set({
      nodes: layoutedNodes,
      edges: layoutedEdges,
      originalConfig: config,
      history: [{ nodes: layoutedNodes, edges: layoutedEdges }],
      currentHistoryIndex: 0,
      selectedNodeId: null,
    });

    return { nodes: layoutedNodes, edges: layoutedEdges };
  },
}));
