import { create } from "zustand";
import {
  CustomNode,
  CustomEdge,
  Position,
  NodeData,
  GraphState,
} from "./types";
import { nanoid } from "nanoid";
import {
  TeamConfig,
  AgentConfig,
  ModelConfig,
  ToolConfig,
  ComponentTypes,
  ComponentConfigTypes,
  TerminationConfig,
} from "../../../types/datamodel";
import { convertTeamConfigToGraph, getLayoutedElements } from "./utils";

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

export interface TeamBuilderState {
  nodes: CustomNode[];
  edges: CustomEdge[];
  selectedNodeId: string | null;
  history: Array<{ nodes: CustomNode[]; edges: CustomEdge[] }>;
  currentHistoryIndex: number;
  originalConfig: TeamConfig | null;
  addNode: (
    type: ComponentTypes,
    position: Position,
    config: ComponentConfigTypes,
    targetNodeId?: string
  ) => void;

  updateNode: (nodeId: string, updates: Partial<NodeData>) => void;
  removeNode: (nodeId: string) => void;

  addEdge: (edge: CustomEdge) => void;
  removeEdge: (edgeId: string) => void;

  setSelectedNode: (nodeId: string | null) => void;

  undo: () => void;
  redo: () => void;

  // Sync with JSON
  syncToJson: () => TeamConfig | null;
  loadFromJson: (config: TeamConfig) => GraphState;
  layoutNodes: () => void;
  resetHistory: () => void;
}

const buildTeamConfig = (
  teamNode: CustomNode,
  nodes: CustomNode[],
  edges: CustomEdge[]
): TeamConfig | null => {
  if (!isTeamConfig(teamNode.data.config)) return null;

  const config = { ...teamNode.data.config };

  // Use edge queries instead of connections
  const modelEdge = edges.find(
    (e) => e.target === teamNode.id && e.type === "model-connection"
  );
  if (modelEdge) {
    const modelNode = nodes.find((n) => n.id === modelEdge.source);
    if (
      modelNode &&
      isModelConfig(modelNode.data.config) &&
      config.team_type === "SelectorGroupChat"
    ) {
      config.model_client = modelNode.data.config;
    }
  }

  // Add termination connection handling
  const terminationEdge = edges.find(
    (e) => e.target === teamNode.id && e.type === "termination-connection"
  );
  if (terminationEdge) {
    const terminationNode = nodes.find((n) => n.id === terminationEdge.source);
    if (terminationNode && isTerminationConfig(terminationNode.data.config)) {
      config.termination_condition = terminationNode.data.config;
    }
  }

  // Get participants using edges
  const participantEdges = edges.filter(
    (e) => e.source === teamNode.id && e.type === "agent-connection"
  );
  config.participants = participantEdges
    .map((edge) => {
      const agentNode = nodes.find((n) => n.id === edge.target);
      if (!agentNode || !isAgentConfig(agentNode.data.config)) return null;

      const agentConfig = { ...agentNode.data.config };

      // Get agent's model using edges
      const agentModelEdge = edges.find(
        (e) => e.target === edge.target && e.type === "model-connection"
      );
      if (agentModelEdge) {
        const modelNode = nodes.find((n) => n.id === agentModelEdge.source);
        if (modelNode && isModelConfig(modelNode.data.config)) {
          agentConfig.model_client = modelNode.data.config;
        }
      }

      // Get agent's tools using edges
      const toolEdges = edges.filter(
        (e) => e.target === edge.target && e.type === "tool-connection"
      );
      agentConfig.tools = toolEdges
        .map((toolEdge) => {
          const toolNode = nodes.find((n) => n.id === toolEdge.source);
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
    set((state) => {
      // Determine label based on config type
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

      // Create new node without connections object
      const newNode: CustomNode = {
        id: nanoid(),
        type,
        position,
        data: {
          label: label || "Node",
          type,
          config,
        },
      };

      let newNodes = [...state.nodes];
      let newEdges = [...state.edges];

      if (targetNodeId) {
        const targetNode = state.nodes.find((n) => n.id === targetNodeId);

        if (targetNode) {
          if (
            type === "model" &&
            ["team", "agent"].includes(targetNode.data.type)
          ) {
            // Find existing model connection and node
            const existingModelEdge = newEdges.find(
              (edge) =>
                edge.target === targetNodeId && edge.type === "model-connection"
            );

            if (existingModelEdge) {
              // Remove the existing model node
              const existingModelNodeId = existingModelEdge.source;
              newNodes = newNodes.filter(
                (node) => node.id !== existingModelNodeId
              );

              // Remove all edges connected to the old model node
              newEdges = newEdges.filter(
                (edge) =>
                  edge.source !== existingModelNodeId &&
                  edge.target !== existingModelNodeId
              );
            }

            // Add the new model node
            newNodes.push(newNode);

            // Add new model connection
            newEdges.push({
              id: nanoid(),
              source: newNode.id,
              target: targetNodeId,
              sourceHandle: `${newNode.id}-model-output-handle`,
              targetHandle: `${targetNodeId}-model-input-handle`,
              type: "model-connection",
            });

            // Update config
            if (
              isTeamConfig(targetNode.data.config) &&
              isModelConfig(config) &&
              targetNode.data.config.team_type === "SelectorGroupChat"
            ) {
              targetNode.data.config.model_client = config;
            } else if (
              isAgentConfig(targetNode.data.config) &&
              isModelConfig(config)
            ) {
              targetNode.data.config.model_client = config;
            }
          } else if (
            type === "termination" &&
            targetNode.data.type === "team"
          ) {
            // Find existing termination connection and node
            const existingTerminationEdge = newEdges.find(
              (edge) =>
                edge.target === targetNodeId &&
                edge.type === "termination-connection"
            );

            if (existingTerminationEdge) {
              // Remove the existing termination node
              const existingTerminationNodeId = existingTerminationEdge.source;
              newNodes = newNodes.filter(
                (node) => node.id !== existingTerminationNodeId
              );

              // Remove all edges connected to the old termination node
              newEdges = newEdges.filter(
                (edge) =>
                  edge.source !== existingTerminationNodeId &&
                  edge.target !== existingTerminationNodeId
              );
            }

            // Add the new termination node
            newNodes.push(newNode);

            // Add new termination connection
            newEdges.push({
              id: nanoid(),
              source: newNode.id,
              target: targetNodeId,
              sourceHandle: `${newNode.id}-termination-output-handle`,
              targetHandle: `${targetNodeId}-termination-input-handle`,
              type: "termination-connection",
            });

            // Update config
            if (
              isTeamConfig(targetNode.data.config) &&
              isTerminationConfig(config)
            ) {
              targetNode.data.config.termination_condition = config;
            }
          } else if (type === "tool" && targetNode.data.type === "agent") {
            // Add tool connection
            newNodes.push(newNode);
            newEdges.push({
              id: nanoid(),
              source: newNode.id,
              target: targetNodeId,
              sourceHandle: `${newNode.id}-tool-output-handle`,
              targetHandle: `${targetNodeId}-tool-input-handle`,
              type: "tool-connection",
            });

            // Update config
            if (isAgentConfig(targetNode.data.config) && isToolConfig(config)) {
              if (!targetNode.data.config.tools) {
                targetNode.data.config.tools = [];
              }
              targetNode.data.config.tools.push(config);
            }
          } else if (type === "agent" && targetNode.data.type === "team") {
            // Add agent connection
            newNodes.push(newNode);
            newEdges.push({
              id: nanoid(),
              source: targetNodeId,
              target: newNode.id,
              sourceHandle: `${targetNodeId}-agent-output-handle`,
              targetHandle: `${newNode.id}-agent-input-handle`,
              type: "agent-connection",
            });

            // Update config
            if (isTeamConfig(targetNode.data.config) && isAgentConfig(config)) {
              if (!targetNode.data.config.participants) {
                targetNode.data.config.participants = [];
              }
              targetNode.data.config.participants.push(config);
            }
          } else {
            // For all other cases, just add the new node
            newNodes.push(newNode);
          }
        }
      } else {
        // If no target node, just add the new node
        newNodes.push(newNode);
      }

      const { nodes: layoutedNodes, edges: layoutedEdges } =
        getLayoutedElements(newNodes, newEdges);

      return {
        nodes: layoutedNodes,
        edges: layoutedEdges,
        history: [
          ...state.history.slice(0, state.currentHistoryIndex + 1),
          { nodes: layoutedNodes, edges: layoutedEdges },
        ].slice(-MAX_HISTORY),
        currentHistoryIndex: state.currentHistoryIndex + 1,
      };
    });
  },

  updateNode: (nodeId: string, updates: Partial<NodeData>) => {
    set((state) => {
      const newNodes = state.nodes.map((node) => {
        if (node.id !== nodeId) return node;

        // Update the node with new data
        const updatedNode = {
          ...node,
          data: {
            ...node.data,
            ...updates,
            // Update label based on config type
            label: (() => {
              const config = { ...node.data.config, ...updates.config };
              if (isTeamConfig(config)) return config.name || "Team";
              if (isAgentConfig(config)) return config.name || "Agent";
              if (isModelConfig(config)) return config.model || "Model";
              if (isToolConfig(config)) return config.name || "Tool";
              if (isTerminationConfig(config))
                return config.termination_type || "Termination";
              return node.data.label;
            })(),
          },
        };

        return updatedNode;
      });

      // Update related nodes' configs
      const updatedNode = newNodes.find((n) => n.id === nodeId);
      if (!updatedNode) return state;

      // If an agent was updated, update its parent team's participants
      if (updatedNode.data.type === "agent") {
        const teamEdge = state.edges.find(
          (e) => e.type === "agent-connection" && e.target === nodeId
        );
        if (teamEdge) {
          newNodes.forEach((node) => {
            if (node.id === teamEdge.source && isTeamConfig(node.data.config)) {
              const agentConfig = updatedNode.data.config as AgentConfig;
              node.data.config.participants = node.data.config.participants.map(
                (p) => (p.name === agentConfig.name ? agentConfig : p)
              );
            }
          });
        }
      }

      // If a tool was updated, update its parent agent's tools
      if (updatedNode.data.type === "tool") {
        const agentEdge = state.edges.find(
          (e) => e.type === "tool-connection" && e.source === nodeId
        );
        if (agentEdge) {
          newNodes.forEach((node) => {
            if (
              node.id === agentEdge.target &&
              isAgentConfig(node.data.config)
            ) {
              const toolConfig = updatedNode.data.config as ToolConfig;
              node.data.config.tools = node.data.config.tools?.map((t) =>
                t.name === toolConfig.name ? toolConfig : t
              );
            }
          });
        }
      }

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
      const nodesToRemove = new Set<string>();

      const collectNodesToRemove = (id: string) => {
        const node = state.nodes.find((n) => n.id === id);
        if (!node) return;

        nodesToRemove.add(id);

        // Find all edges connected to this node
        const connectedEdges = state.edges.filter(
          (edge) => edge.source === id || edge.target === id
        );

        // Handle cascading deletes based on node type
        if (node.data.type === "team") {
          // Find and remove all agents
          connectedEdges
            .filter((e) => e.type === "agent-connection")
            .forEach((e) => collectNodesToRemove(e.target));

          // Remove team's model if exists
          connectedEdges
            .filter((e) => e.type === "model-connection")
            .forEach((e) => collectNodesToRemove(e.source));

          // Remove termination condition if exists
          connectedEdges
            .filter((e) => e.type === "termination-connection")
            .forEach((e) => collectNodesToRemove(e.source));
        } else if (node.data.type === "agent") {
          // Remove agent's model if exists
          connectedEdges
            .filter((e) => e.type === "model-connection")
            .forEach((e) => collectNodesToRemove(e.source));

          // Remove all agent's tools
          connectedEdges
            .filter((e) => e.type === "tool-connection")
            .forEach((e) => collectNodesToRemove(e.source));

          // Also need to remove agent from team's config
          const teamEdge = connectedEdges.find(
            (e) => e.type === "agent-connection"
          );
          if (teamEdge) {
            const teamNode = state.nodes.find((n) => n.id === teamEdge.source);
            if (teamNode && isTeamConfig(teamNode.data.config)) {
              const agentConfig = node.data.config as AgentConfig;
              teamNode.data.config.participants =
                teamNode.data.config.participants.filter(
                  (p) => p.name !== agentConfig.name
                );
            }
          }
        } else if (node.data.type === "tool") {
          // Update agent's tools array when removing a tool
          const agentEdge = connectedEdges.find(
            (e) => e.type === "tool-connection"
          );
          if (agentEdge) {
            const agentNode = state.nodes.find(
              (n) => n.id === agentEdge.target
            );
            if (agentNode && isAgentConfig(agentNode.data.config)) {
              const toolConfig = node.data.config as ToolConfig;
              agentNode.data.config.tools = agentNode.data.config.tools?.filter(
                (t) => t.name !== toolConfig.name
              );
            }
          }
        } else if (node.data.type === "termination") {
          // Update team's termination condition when removing it
          const teamEdge = connectedEdges.find(
            (e) => e.type === "termination-connection"
          );
          if (teamEdge) {
            const teamNode = state.nodes.find((n) => n.id === teamEdge.target);
            if (teamNode && isTeamConfig(teamNode.data.config)) {
              teamNode.data.config.termination_condition = undefined;
            }
          }
        }
      };

      // Start the cascade deletion from the initial node
      collectNodesToRemove(nodeId);

      // Remove all collected nodes
      const newNodes = state.nodes.filter(
        (node) => !nodesToRemove.has(node.id)
      );

      // Remove all affected edges
      const newEdges = state.edges.filter(
        (edge) =>
          !nodesToRemove.has(edge.source) && !nodesToRemove.has(edge.target)
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

    set((state) => {
      return {
        nodes: layoutedNodes,
        edges: layoutedEdges,
        originalConfig: config,
        history: [{ nodes: layoutedNodes, edges: layoutedEdges }], // Reset history
        currentHistoryIndex: 0, // Reset to 0
        selectedNodeId: null,
      };
    });

    return { nodes: layoutedNodes, edges: layoutedEdges };
  },
  resetHistory: () => {
    set((state) => ({
      history: [{ nodes: state.nodes, edges: state.edges }],
      currentHistoryIndex: 0,
    }));
  },
}));
