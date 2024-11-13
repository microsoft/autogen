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
import { ThreadState, ThreadStatus } from "../types";
import { CustomEdge, EdgeTooltipContent } from "./edge";
import { Tooltip } from "antd";

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

const NODE_DIMENSIONS = {
  default: { width: 150, height: 100 },
  end: { width: 120, height: 80 },
};

const getLayoutedElements = (
  nodes: Node[],
  edges: Edge[],
  direction: "TB" | "LR"
) => {
  const g = new Dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));
  g.setGraph({
    rankdir: direction,
    nodesep: direction === "TB" ? 100 : 80, // Adjust for orientation
    ranksep: direction === "TB" ? 80 : 100, // Adjust for orientation
    align: direction === "TB" ? "DL" : "UL", // Adjust alignment
    ranker: "network-simplex",
    marginx: 30,
    marginy: 30,
  });

  edges.forEach((edge) => g.setEdge(edge.source, edge.target));
  nodes.forEach((node) => {
    const dimensions =
      node.data.type === "end" ? NODE_DIMENSIONS.end : NODE_DIMENSIONS.default;
    g.setNode(node.id, { ...node, ...dimensions });
  });

  Dagre.layout(g);

  return {
    nodes: nodes.map((node) => {
      const { x, y } = g.node(node.id);
      const dimensions =
        node.data.type === "end"
          ? NODE_DIMENSIONS.end
          : NODE_DIMENSIONS.default;
      return {
        ...node,
        position: {
          x: x - dimensions.width / 2,
          y: y - dimensions.height / 2,
        },
      };
    }),
    edges,
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

      const sequences: MessageSequence[] = [];
      const nodeMap = new Map<string, Node>();
      const transitionCounts = new Map<string, MessageSequence>();

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

      // Group messages by transitions (including self-transitions)
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

      // Create edges from transitions
      const newEdges: Edge[] = Array.from(transitionCounts.entries()).map(
        ([key, transition], index) => {
          // const avgTokens = Math.round(
          //   transition.totalTokens / transition.count
          // );
          const label =
            transition.totalTokens > 0
              ? `${transition.count > 1 ? `${transition.count}x` : ""} (${
                  transition.totalTokens
                } tokens)`
              : "";

          return {
            id: `${transition.source}-${transition.target}-${index}`,
            source: transition.source,
            target: transition.target,
            type: "custom",
            data: {
              label,
              messages: transition.messages,
            },
            animated:
              threadState?.status === "streaming" &&
              index === transitionCounts.size - 1,
            style: {
              stroke: "#2563eb",
              strokeWidth: Math.min(Math.max(transition.count, 1), 5),
              // Add curved style for self-referential edges
              ...(transition.source === transition.target && {
                borderRadius: 20,
                curvature: 0.5,
              }),
            },
          };
        }
      );

      // Handle end node logic (keeping existing end node logic)
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
            animated: false,
            style: {
              stroke: edgeColor,
              opacity: 1,
              zIndex: 100,
            },
          });
        }
      }

      // Set active state for the last message source
      const lastActiveSource = messages[messages.length - 1]?.source;
      nodeMap.forEach((node) => {
        node.data.isActive =
          node.id === lastActiveSource && threadState?.status === "streaming";
      });

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
