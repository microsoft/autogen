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

interface AgentFlowProps {
  teamConfig: TeamConfig;
  messages: AgentMessageConfig[];
  threadState: ThreadState;
  direction?: "TB" | "LR";
}

interface MessageSequence {
  source: string;
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
  g.setGraph({ rankdir: direction });

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

const AgentFlow: React.FC<AgentFlowProps> = ({
  teamConfig,
  messages,
  threadState,
  direction = "TB",
}) => {
  const { fitView } = useReactFlow();
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);

  const processMessages = useCallback(
    (messages: AgentMessageConfig[]) => {
      if (messages.length === 0) return { nodes: [], edges: [] };

      const sequences: MessageSequence[] = [];
      const nodeMap = new Map<string, Node>();

      let currentSequence: MessageSequence = {
        source: messages[0].source,
        count: 1,
        totalTokens:
          (messages[0].models_usage?.prompt_tokens || 0) +
          (messages[0].models_usage?.completion_tokens || 0),
        messages: [messages[0]],
      };

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

      // Process remaining messages
      for (let i = 1; i < messages.length; i++) {
        const message = messages[i];
        const tokens =
          (message.models_usage?.prompt_tokens || 0) +
          (message.models_usage?.completion_tokens || 0);

        if (message.source === currentSequence.source) {
          currentSequence.count++;
          currentSequence.totalTokens += tokens;
          currentSequence.messages.push(message);
        } else {
          sequences.push(currentSequence);
          currentSequence = {
            source: message.source,
            count: 1,
            totalTokens: tokens,
            messages: [message],
          };

          if (!nodeMap.has(message.source)) {
            const agentConfig = teamConfig.participants.find(
              (p) => p.name === message.source
            );
            nodeMap.set(
              message.source,
              createNode(
                message.source,
                message.source === "user" ? "user" : "agent",
                agentConfig,
                false
              )
            );
          }
        }
      }
      sequences.push(currentSequence);

      // Create edges
      const newEdges: Edge[] = [];
      for (let i = 0; i < sequences.length - 1; i++) {
        const current = sequences[i];
        const next = sequences[i + 1];

        let label = "";
        if (current.source === next.source && current.count > 1) {
          const avgTokens = Math.round(current.totalTokens / current.count);
          label = `${current.count}x (${avgTokens} tokens/msg)`;
        }

        newEdges.push({
          id: `${current.source}-${next.source}-${i}`,
          source: current.source,
          target: next.source,
          label,
          animated:
            threadState?.status === "streaming" && i === sequences.length - 2,
          style: {
            stroke: "#2563eb",
            strokeWidth: Math.min(Math.max(current.count, 1), 5),
          },
          labelStyle: {
            fill: "#94a3b8",
            fontSize: 12,
            fontFamily: "monospace",
          },
          type: "smoothstep",
        });
      }

      // Add end node for non-streaming states - MODIFIED THIS SECTION
      if (threadState && sequences.length > 0) {
        const lastSequence = sequences[sequences.length - 1];

        // Always create the end node, but style it differently based on status
        if (["complete", "error", "cancelled"].includes(threadState.status)) {
          nodeMap.set(
            "end",
            createNode("end", "end", undefined, false, threadState)
          );

          const edgeColor =
            {
              streaming: "#2563eb",
              complete: "var(--accent)",
              cancelled: "var(--secondary)",
              error: "rgb(239 68 68)",
            }[threadState.status] || "#2563eb";

          newEdges.push({
            id: `${lastSequence.source}-end`,
            source: lastSequence.source,
            target: "end",
            animated: false,
            style: {
              stroke: edgeColor,
              strokeWidth: 2,
            },
            type: "smoothstep",
          });
        }
      }

      // Set active state for the last message source only
      const lastActiveSource = sequences[sequences.length - 1]?.source;
      nodeMap.forEach((node) => {
        node.data.isActive =
          node.id === lastActiveSource && threadState?.status === "streaming";
      });

      return {
        nodes: Array.from(nodeMap.values()),
        edges: newEdges,
      };
    },
    [teamConfig.participants, threadState] // Added threadState to dependencies
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
    console.log("threadstate", threadState);
  }, [messages, processMessages, direction, threadState, fitView]);

  return (
    <div className="w-full h-full bg-tertiary rounded-lg min-h-[300px]">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
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
