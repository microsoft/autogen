import React, { useCallback, useState, useEffect } from "react";
import {
  ReactFlow,
  Node,
  Edge,
  Background,
  Controls,
  NodeTypes,
  useReactFlow,
  ReactFlowProvider,
} from "@xyflow/react";
import Dagre from "@dagrejs/dagre";
import "@xyflow/react/dist/style.css";
import AgentNode from "./agentnode";
import {
  AgentMessageConfig,
  AgentConfig,
  TeamConfig,
} from "../../../../types/datamodel";
import { ThreadState } from "../types";
import { CustomEdge } from "./edge";

interface AgentFlowProps {
  teamConfig: TeamConfig;
  messages: AgentMessageConfig[];
  threadState: ThreadState;
  direction?: "TB" | "LR";
}

interface MessageSequence {
  source: string;
  target: string;
  count: number;
  totalTokens: number;
  messages: AgentMessageConfig[];
}

interface BidirectionalPattern {
  forward: MessageSequence;
  reverse: MessageSequence;
}

const NODE_DIMENSIONS = {
  default: { width: 150, height: 100 },
  end: { width: 120, height: 80 },
};

const getLayoutedElements = (
  nodes: Node[],
  edges: Edge[],
  direction: "TB" | "LR"
) => {
  // First pass: Basic node positioning with Dagre
  const g = new Dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));

  g.setGraph({
    rankdir: direction,
    nodesep: 80, // Reduced horizontal separation
    ranksep: 120, // Increased vertical separation
    ranker: "network-simplex",
    align: "DL", // Prefer left alignment within ranks
    marginx: 30,
    marginy: 30,
  });

  // Add nodes
  nodes.forEach((node) => {
    const dimensions =
      node.data.type === "end" ? NODE_DIMENSIONS.end : NODE_DIMENSIONS.default;
    g.setNode(node.id, { ...node, ...dimensions });
  });

  // Add basic edges for layout (one per pair of nodes)
  const processedPairs = new Set<string>();
  edges.forEach((edge) => {
    const pairKey = [edge.source, edge.target].sort().join("-");
    if (!processedPairs.has(pairKey)) {
      g.setEdge(edge.source, edge.target, { weight: 1 });
      processedPairs.add(pairKey);
    }
  });

  // Run layout
  Dagre.layout(g);

  // Second pass: Position nodes and create edge paths
  const positionedNodes = nodes.map((node) => {
    const { x, y } = g.node(node.id);
    const dimensions =
      node.data.type === "end" ? NODE_DIMENSIONS.end : NODE_DIMENSIONS.default;
    return {
      ...node,
      position: {
        x: x - dimensions.width / 2,
        y: y - dimensions.height / 2,
      },
    };
  });

  // Create a map of node positions for edge calculations
  const nodePositions = new Map(
    positionedNodes.map((node) => [
      node.id,
      {
        x: node.position.x + NODE_DIMENSIONS.default.width / 2,
        y: node.position.y + NODE_DIMENSIONS.default.height / 2,
      },
    ])
  );

  // Process edges based on their type (self-loop, bidirectional, or normal)
  const positionedEdges = edges.map((edge) => {
    const sourcePos = nodePositions.get(edge.source)!;
    const targetPos = nodePositions.get(edge.target)!;

    return {
      ...edge,
      sourceX: sourcePos.x,
      sourceY: sourcePos.y,
      targetX: targetPos.x,
      targetY: targetPos.y,
    };
  });

  return {
    nodes: positionedNodes,
    edges: positionedEdges,
  };
};

const createNode = (
  id: string,
  type: "user" | "agent" | "end",
  agentConfig?: AgentConfig,
  isActive: boolean = false,
  threadState?: ThreadState
): Node => {
  if (type === "user") {
    return {
      id,
      type: "agentNode",
      position: { x: 0, y: 0 },
      data: {
        type: "user",
        label: "User",
        agentType: "user",
        description: "Human user",
        isActive,
        status: "",
        reason: "",
      },
    };
  }

  if (type === "end") {
    return {
      id,
      type: "agentNode",
      position: { x: 0, y: 0 },
      data: {
        type: "end",
        label: "End",
        status: threadState?.status,
        reason: threadState?.reason || "",
        agentType: "",
        description: "",
        isActive: false,
      },
    };
  }

  return {
    id,
    type: "agentNode",
    position: { x: 0, y: 0 },
    data: {
      type: "agent",
      label: id,
      agentType: agentConfig?.agent_type || "",
      description: agentConfig?.description || "",
      isActive,
      status: "",
      reason: "",
    },
  };
};

const nodeTypes: NodeTypes = {
  agentNode: AgentNode,
};

const edgeTypes = {
  custom: CustomEdge,
};

const AgentFlow: React.FC<AgentFlowProps> = ({
  teamConfig,
  messages,
  threadState,
  direction = "TB",
}) => {
  const { fitView } = useReactFlow();
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);

  // ...previous imports remain same

  const processMessages = useCallback(
    (messages: AgentMessageConfig[]) => {
      if (messages.length === 0) return { nodes: [], edges: [] };

      const nodeMap = new Map<string, Node>();
      const transitionCounts = new Map<string, MessageSequence>();
      const bidirectionalPatterns = new Map<string, BidirectionalPattern>();

      // Process first message source
      const firstAgentConfig = teamConfig.participants.find(
        (p) => p.name === messages[0].source
      );
      nodeMap.set(
        messages[0].source,
        createNode(
          messages[0].source,
          messages[0].source === "user" ? "user" : "agent",
          firstAgentConfig,
          false
        )
      );

      // Group messages by transitions
      for (let i = 0; i < messages.length - 1; i++) {
        const currentMsg = messages[i];
        const nextMsg = messages[i + 1];
        const transitionKey = `${currentMsg.source}->${nextMsg.source}`;

        if (!transitionCounts.has(transitionKey)) {
          transitionCounts.set(transitionKey, {
            source: currentMsg.source,
            target: nextMsg.source,
            count: 1,
            totalTokens:
              (currentMsg.models_usage?.prompt_tokens || 0) +
              (currentMsg.models_usage?.completion_tokens || 0),
            messages: [currentMsg],
          });
        } else {
          const transition = transitionCounts.get(transitionKey)!;
          transition.count++;
          transition.totalTokens +=
            (currentMsg.models_usage?.prompt_tokens || 0) +
            (currentMsg.models_usage?.completion_tokens || 0);
          transition.messages.push(currentMsg);
        }

        // Ensure all nodes are in the nodeMap
        if (!nodeMap.has(nextMsg.source)) {
          const agentConfig = teamConfig.participants.find(
            (p) => p.name === nextMsg.source
          );
          nodeMap.set(
            nextMsg.source,
            createNode(
              nextMsg.source,
              nextMsg.source === "user" ? "user" : "agent",
              agentConfig,
              false
            )
          );
        }
      }

      // Identify bidirectional patterns
      transitionCounts.forEach((transition, key) => {
        const [source, target] = key.split("->");
        const reverseKey = `${target}->${source}`;
        const reverseTransition = transitionCounts.get(reverseKey);

        if (reverseTransition && !bidirectionalPatterns.has(key)) {
          const patternKey = [source, target].sort().join("->");
          bidirectionalPatterns.set(patternKey, {
            forward: transition,
            reverse: reverseTransition,
          });
        }
      });

      // Create edges with bidirectional routing
      const newEdges: Edge[] = [];
      const processedKeys = new Set<string>();

      transitionCounts.forEach((transition, key) => {
        if (processedKeys.has(key)) return;

        const [source, target] = key.split("->");
        const patternKey = [source, target].sort().join("->");
        const bidirectionalPattern = bidirectionalPatterns.get(patternKey);

        if (bidirectionalPattern) {
          // Create paired edges for bidirectional pattern
          const forwardKey = `${source}->${target}`;
          const reverseKey = `${target}->${source}`;

          const forwardEdgeId = `${source}-${target}-forward`;
          const reverseEdgeId = `${target}-${source}-reverse`;

          const createBidirectionalEdge = (
            transition: MessageSequence,
            isSecondary: boolean,
            edgeId: string,
            pairedEdgeId: string
          ) => ({
            id: edgeId,
            source: transition.source,
            target: transition.target,
            type: "custom",
            data: {
              label:
                transition.totalTokens > 0
                  ? `${transition.count > 1 ? `${transition.count}x` : ""} (${
                      transition.totalTokens
                    } tokens)`
                  : "",
              messages: transition.messages,
              routingType: isSecondary ? "secondary" : "primary",
              bidirectionalPair: pairedEdgeId,
            },
            style: {
              stroke: "#2563eb",
              strokeWidth: 1,
            },
          });

          newEdges.push(
            createBidirectionalEdge(
              transitionCounts.get(forwardKey)!,
              false,
              forwardEdgeId,
              reverseEdgeId
            ),
            createBidirectionalEdge(
              transitionCounts.get(reverseKey)!,
              true,
              reverseEdgeId,
              forwardEdgeId
            )
          );

          processedKeys.add(forwardKey);
          processedKeys.add(reverseKey);
        } else {
          // Handle regular edges (including self-loops)
          newEdges.push({
            id: `${transition.source}-${transition.target}-${key}`,
            source: transition.source,
            target: transition.target,
            type: "custom",
            data: {
              label:
                transition.totalTokens > 0
                  ? `${transition.count > 1 ? `${transition.count}x` : ""} (${
                      transition.totalTokens
                    } tokens)`
                  : "",
              messages: transition.messages,
            },
            animated:
              threadState?.status === "streaming" &&
              key === Array.from(transitionCounts.keys()).pop(),
            style: {
              stroke: "#2563eb",
              strokeWidth: 1,
            },
          });
        }
      });

      // Handle end node logic
      if (threadState && messages.length > 0) {
        const lastMessage = messages[messages.length - 1];

        if (["complete", "error", "cancelled"].includes(threadState.status)) {
          nodeMap.set(
            "end",
            createNode("end", "end", undefined, false, threadState)
          );

          const edgeColor =
            {
              complete: "#2563eb",
              cancelled: "red",
              error: "red",
              streaming: "#2563eb",
              awaiting_input: "#2563eb",
              timeout: "red",
            }[threadState.status] || "#2563eb";

          newEdges.push({
            id: `${lastMessage.source}-end`,
            source: lastMessage.source,
            target: "end",
            type: "custom",
            data: {
              label: "ended",
              messages: [],
            },
            style: {
              stroke: edgeColor,
              strokeWidth: 1,
              opacity: 1,
              zIndex: 100,
            },
          });
        }
      }

      return {
        nodes: Array.from(nodeMap.values()),
        edges: newEdges,
      };
    },
    [teamConfig.participants, threadState]
  );

  useEffect(() => {
    const { nodes: newNodes, edges: newEdges } = processMessages(messages);
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      newNodes,
      newEdges,
      direction
    );

    setNodes(layoutedNodes);
    setEdges(layoutedEdges);

    if (messages.length > 0) {
      setTimeout(() => {
        fitView({ padding: 0.2, duration: 200 });
      }, 50);
    }
  }, [messages, processMessages, direction, threadState, fitView]);

  return (
    <div className="w-full h-full bg-tertiary rounded-lg min-h-[300px]">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        defaultViewport={{ x: 0, y: 0, zoom: 1 }}
        minZoom={0.5}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
        onInit={() => {
          if (messages.length > 0) {
            setTimeout(() => {
              fitView({ padding: 0.2, duration: 200 });
            }, 50);
          }
        }}
      >
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
};

export default function WrappedAgentFlow(props: AgentFlowProps) {
  return (
    <ReactFlowProvider>
      <AgentFlow {...props} />
    </ReactFlowProvider>
  );
}
