// builder/store.tsx
import { create } from "zustand";
import { isEqual } from "lodash";
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
  ToolConfig,
  Component,
  ComponentConfig,
} from "../../../types/datamodel";
import {
  convertTeamConfigToGraph,
  getLayoutedElements,
  getUniqueName,
} from "./utils";
import {
  isTeamComponent,
  isAgentComponent,
  isToolComponent,
  isTerminationComponent,
  isModelComponent,
  isSelectorTeam,
  isAssistantAgent,
  isFunctionTool,
} from "../../../types/guards";

const MAX_HISTORY = 50;

export interface TeamBuilderState {
  nodes: CustomNode[];
  edges: CustomEdge[];
  selectedNodeId: string | null;
  history: Array<{ nodes: CustomNode[]; edges: CustomEdge[] }>;
  currentHistoryIndex: number;
  originalComponent: Component<TeamConfig> | null;
  addNode: (
    position: Position,
    component: Component<ComponentConfig>,
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
  syncToJson: () => Component<TeamConfig> | null;
  loadFromJson: (config: Component<TeamConfig>) => GraphState;
  layoutNodes: () => void;
  resetHistory: () => void;
}

const buildTeamComponent = (
  teamNode: CustomNode,
  nodes: CustomNode[],
  edges: CustomEdge[]
): Component<TeamConfig> | null => {
  if (!isTeamComponent(teamNode.data.component)) return null;

  const component = { ...teamNode.data.component };

  // Use edge queries instead of connections
  const modelEdge = edges.find(
    (e) => e.target === teamNode.id && e.type === "model-connection"
  );
  if (modelEdge) {
    const modelNode = nodes.find((n) => n.id === modelEdge.source);
    if (
      modelNode &&
      isModelComponent(modelNode.data.component) &&
      isSelectorTeam(component)
    ) {
      component.config.model_client = modelNode.data.component;
    }
  }

  // Add termination connection handling
  const terminationEdge = edges.find(
    (e) => e.target === teamNode.id && e.type === "termination-connection"
  );
  if (terminationEdge) {
    const terminationNode = nodes.find((n) => n.id === terminationEdge.source);
    // if (terminationNode && isTerminationConfig(terminationNode.data.config)) {
    //   config.termination_condition = terminationNode.data.config;
    // }
    if (
      terminationNode &&
      isTerminationComponent(terminationNode.data.component)
    ) {
      component.config.termination_condition = terminationNode.data.component;
    }
  }

  // Get participants using edges
  const participantEdges = edges.filter(
    (e) => e.source === teamNode.id && e.type === "agent-connection"
  );
  component.config.participants = participantEdges
    .map((edge) => {
      const agentNode = nodes.find((n) => n.id === edge.target);
      if (!agentNode || !isAgentComponent(agentNode.data.component))
        return null;

      const agentComponent = { ...agentNode.data.component };
      // Get agent's model using edges
      const agentModelEdge = edges.find(
        (e) => e.target === edge.target && e.type === "model-connection"
      );
      if (agentModelEdge) {
        const modelNode = nodes.find((n) => n.id === agentModelEdge.source);
        if (
          modelNode &&
          isModelComponent(modelNode.data.component) &&
          isAssistantAgent(agentComponent)
        ) {
          // Check specific agent type
          agentComponent.config.model_client = modelNode.data.component;
        }
      }

      // Get agent's tools using edges
      const toolEdges = edges.filter(
        (e) => e.target === edge.target && e.type === "tool-connection"
      );

      if (isAssistantAgent(agentComponent)) {
        agentComponent.config.tools = toolEdges
          .map((toolEdge) => {
            const toolNode = nodes.find((n) => n.id === toolEdge.source);
            if (toolNode && isToolComponent(toolNode.data.component)) {
              return toolNode.data.component;
            }
            return null;
          })
          .filter((tool): tool is Component<ToolConfig> => tool !== null);
      }

      return agentComponent;
    })
    .filter((agent): agent is Component<AgentConfig> => agent !== null);

  return component;
};

export const useTeamBuilderStore = create<TeamBuilderState>((set, get) => ({
  nodes: [],
  edges: [],
  selectedNodeId: null,
  history: [],
  currentHistoryIndex: -1,
  originalComponent: null,

  addNode: (
    position: Position,
    component: Component<ComponentConfig>,
    targetNodeId?: string
  ) => {
    set((state) => {
      // Deep clone the incoming component to avoid reference issues
      const clonedComponent = JSON.parse(JSON.stringify(component));

      // Determine label based on component type
      let label = clonedComponent.label || clonedComponent.component_type;

      // Create new node
      const newNode: CustomNode = {
        id: nanoid(),
        position,
        type: clonedComponent.component_type,
        data: {
          label: label || "Node",
          component: clonedComponent,
          type: clonedComponent.component_type as NodeData["type"],
        },
      };

      let newNodes = [...state.nodes];
      let newEdges = [...state.edges];

      if (targetNodeId) {
        const targetNode = state.nodes.find((n) => n.id === targetNodeId);

        if (targetNode) {
          if (
            clonedComponent.component_type === "model" &&
            (isTeamComponent(targetNode.data.component) ||
              isAgentComponent(targetNode.data.component))
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
            if (isModelComponent(clonedComponent)) {
              if (isSelectorTeam(targetNode.data.component)) {
                targetNode.data.component.config.model_client = clonedComponent;
              } else if (isAssistantAgent(targetNode.data.component)) {
                targetNode.data.component.config.model_client = clonedComponent;
              }
            }
          } else if (
            clonedComponent.component_type === "termination" &&
            targetNode.data.type === "team"
          ) {
            // Handle termination connection
            const existingTerminationEdge = newEdges.find(
              (edge) =>
                edge.target === targetNodeId &&
                edge.type === "termination-connection"
            );

            if (existingTerminationEdge) {
              const existingTerminationNodeId = existingTerminationEdge.source;
              newNodes = newNodes.filter(
                (node) => node.id !== existingTerminationNodeId
              );
              newEdges = newEdges.filter(
                (edge) =>
                  edge.source !== existingTerminationNodeId &&
                  edge.target !== existingTerminationNodeId
              );
            }

            newNodes.push(newNode);
            newEdges.push({
              id: nanoid(),
              source: newNode.id,
              target: targetNodeId,
              sourceHandle: `${newNode.id}-termination-output-handle`,
              targetHandle: `${targetNodeId}-termination-input-handle`,
              type: "termination-connection",
            });

            if (
              isTeamComponent(targetNode.data.component) &&
              isTerminationComponent(clonedComponent)
            ) {
              targetNode.data.component.config.termination_condition =
                clonedComponent;
            }
          } else if (
            clonedComponent.component_type === "tool" &&
            targetNode.data.type === "agent"
          ) {
            // Handle tool connection with unique name
            if (
              isAssistantAgent(targetNode.data.component) &&
              isAssistantAgent(newNode.data.component)
            ) {
              const existingTools =
                targetNode.data.component.config.tools || [];
              const existingNames = existingTools.map((t) => t.config.name);
              newNode.data.component.config.name = getUniqueName(
                clonedComponent.config.name,
                existingNames
              );
            }

            newNodes.push(newNode);
            newEdges.push({
              id: nanoid(),
              source: newNode.id,
              target: targetNodeId,
              sourceHandle: `${newNode.id}-tool-output-handle`,
              targetHandle: `${targetNodeId}-tool-input-handle`,
              type: "tool-connection",
            });

            if (
              isAssistantAgent(targetNode.data.component) &&
              isToolComponent(newNode.data.component)
            ) {
              if (!targetNode.data.component.config.tools) {
                targetNode.data.component.config.tools = [];
              }
              targetNode.data.component.config.tools.push(
                newNode.data.component
              );
            }
          } else if (
            clonedComponent.component_type === "agent" &&
            isTeamComponent(targetNode.data.component) &&
            isAssistantAgent(newNode.data.component)
          ) {
            // Handle agent connection with unique name
            const existingParticipants =
              targetNode.data.component.config.participants || [];
            const existingNames = existingParticipants.map(
              (p) => p.config.name
            );

            newNode.data.component.config.name = getUniqueName(
              clonedComponent.config.name,
              existingNames
            );

            newNodes.push(newNode);
            newEdges.push({
              id: nanoid(),
              source: targetNodeId,
              target: newNode.id,
              sourceHandle: `${targetNodeId}-agent-output-handle`,
              targetHandle: `${newNode.id}-agent-input-handle`,
              type: "agent-connection",
            });

            if (
              isTeamComponent(targetNode.data.component) &&
              isAgentComponent(newNode.data.component)
            ) {
              if (!targetNode.data.component.config.participants) {
                targetNode.data.component.config.participants = [];
              }
              targetNode.data.component.config.participants.push(
                newNode.data.component
              );
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
        if (node.id !== nodeId) {
          // If this isn't the directly updated node, check if it needs related updates
          const isTeamWithUpdatedAgent =
            isTeamComponent(node.data.component) &&
            state.edges.some(
              (e) =>
                e.type === "agent-connection" &&
                e.target === nodeId &&
                e.source === node.id
            );

          if (isTeamWithUpdatedAgent && isTeamComponent(node.data.component)) {
            return {
              ...node,
              data: {
                ...node.data,
                component: {
                  ...node.data.component,
                  config: {
                    ...node.data.component.config,
                    participants: node.data.component.config.participants.map(
                      (participant) =>
                        participant ===
                        state.nodes.find((n) => n.id === nodeId)?.data.component
                          ? updates.component
                          : participant
                    ),
                  },
                },
              },
            };
          }

          const isAgentWithUpdatedTool =
            isAssistantAgent(node.data.component) &&
            state.edges.some(
              (e) =>
                e.type === "tool-connection" &&
                e.source === nodeId &&
                e.target === node.id
            );

          if (isAgentWithUpdatedTool && isAssistantAgent(node.data.component)) {
            return {
              ...node,
              data: {
                ...node.data,
                component: {
                  ...node.data.component,
                  config: {
                    ...node.data.component.config,
                    tools: (node.data.component.config.tools || []).map(
                      (tool) =>
                        tool ===
                        state.nodes.find((n) => n.id === nodeId)?.data.component
                          ? updates.component
                          : tool
                    ),
                  },
                },
              },
            };
          }

          return node;
        }

        // This is the directly updated node
        const updatedComponent = updates.component || node.data.component;
        return {
          ...node,
          data: {
            ...node.data,
            ...updates,
            component: updatedComponent,
          },
        };
      });

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
      const updatedNodes = new Map<string, CustomNode>();

      const collectNodesToRemove = (id: string) => {
        const node = state.nodes.find((n) => n.id === id);
        if (!node) return;

        nodesToRemove.add(id);

        // Find all edges connected to this node
        const connectedEdges = state.edges.filter(
          (edge) => edge.source === id || edge.target === id
        );

        // Handle cascading deletes based on component type
        if (isTeamComponent(node.data.component)) {
          // Find and remove all connected agents
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
        } else if (isAgentComponent(node.data.component)) {
          // Remove agent's model if exists
          connectedEdges
            .filter((e) => e.type === "model-connection")
            .forEach((e) => collectNodesToRemove(e.source));

          // Remove all agent's tools
          connectedEdges
            .filter((e) => e.type === "tool-connection")
            .forEach((e) => collectNodesToRemove(e.source));

          // Update team's participants if agent is connected to a team
          const teamEdge = connectedEdges.find(
            (e) => e.type === "agent-connection"
          );
          if (teamEdge) {
            const teamNode = state.nodes.find((n) => n.id === teamEdge.source);
            if (teamNode && isTeamComponent(teamNode.data.component)) {
              // Create updated team node with filtered participants
              const updatedTeamNode = {
                ...teamNode,
                data: {
                  ...teamNode.data,
                  component: {
                    ...teamNode.data.component,
                    config: {
                      ...teamNode.data.component.config,
                      participants:
                        teamNode.data.component.config.participants.filter(
                          (p) => {
                            // Find a node that matches this participant but isn't being deleted
                            const participantNode = state.nodes.find(
                              (n) =>
                                !nodesToRemove.has(n.id) &&
                                isEqual(n.data.component, p)
                            );
                            return participantNode !== undefined;
                          }
                        ),
                    },
                  },
                },
              };
              updatedNodes.set(teamNode.id, updatedTeamNode);
            }
          }
        } else if (isToolComponent(node.data.component)) {
          // Update connected agent's tools array
          const agentEdge = connectedEdges.find(
            (e) => e.type === "tool-connection"
          );
          if (agentEdge) {
            const agentNode = state.nodes.find(
              (n) => n.id === agentEdge.target
            );
            if (agentNode && isAssistantAgent(agentNode.data.component)) {
              // Create updated agent node with filtered tools
              const updatedAgentNode = {
                ...agentNode,
                data: {
                  ...agentNode.data,
                  component: {
                    ...agentNode.data.component,
                    config: {
                      ...agentNode.data.component.config,
                      tools: (
                        agentNode.data.component.config.tools || []
                      ).filter((t) => {
                        // Find a node that matches this tool but isn't being deleted
                        const toolNode = state.nodes.find(
                          (n) =>
                            !nodesToRemove.has(n.id) &&
                            isEqual(n.data.component, t)
                        );
                        return toolNode !== undefined;
                      }),
                    },
                  },
                },
              };
              updatedNodes.set(agentNode.id, updatedAgentNode);
            }
          }
        } else if (isTerminationComponent(node.data.component)) {
          // Update connected team's termination condition
          const teamEdge = connectedEdges.find(
            (e) => e.type === "termination-connection"
          );
          if (teamEdge) {
            const teamNode = state.nodes.find((n) => n.id === teamEdge.target);
            if (teamNode && isTeamComponent(teamNode.data.component)) {
              const updatedTeamNode = {
                ...teamNode,
                data: {
                  ...teamNode.data,
                  component: {
                    ...teamNode.data.component,
                    config: {
                      ...teamNode.data.component.config,
                      termination_condition: undefined,
                    },
                  },
                },
              };
              updatedNodes.set(teamNode.id, updatedTeamNode);
            }
          }
        }
      };

      // Start the cascade deletion from the initial node
      collectNodesToRemove(nodeId);

      // Create new nodes array with both removals and updates
      const newNodes = state.nodes
        .filter((node) => !nodesToRemove.has(node.id))
        .map((node) => updatedNodes.get(node.id) || node);

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
    const teamNodes = state.nodes.filter(
      (node) => node.data.component.component_type === "team"
    );
    if (teamNodes.length === 0) return null;

    const teamNode = teamNodes[0];
    return buildTeamComponent(teamNode, state.nodes, state.edges);
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

  loadFromJson: (component: Component<TeamConfig>) => {
    // Get graph representation of team config
    const { nodes, edges } = convertTeamConfigToGraph(component);

    // Apply layout to elements
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      nodes,
      edges
    );

    // Update store with new state and reset history
    set({
      nodes: layoutedNodes,
      edges: layoutedEdges,
      originalComponent: component, // Store original component for reference
      history: [{ nodes: layoutedNodes, edges: layoutedEdges }], // Reset history with initial state
      currentHistoryIndex: 0,
      selectedNodeId: null,
    });

    // Return final graph state
    return { nodes: layoutedNodes, edges: layoutedEdges };
  },
  resetHistory: () => {
    set((state) => ({
      history: [{ nodes: state.nodes, edges: state.edges }],
      currentHistoryIndex: 0,
    }));
  },
}));
