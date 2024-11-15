import React, {
  useCallback,
  useState,
  useEffect,
  useRef,
  useMemo,
} from "react";
import {
  ReactFlow,
  Node,
  Edge,
  Background,
  Controls,
  NodeTypes,
  useReactFlow,
  ReactFlowProvider,
  NodeChange,
  applyNodeChanges,
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
import { useConfigStore } from "../../../../../hooks/store";
import { AgentFlowToolbar } from "./toolbar";

interface AgentFlowProps {
  teamConfig: TeamConfig;
  messages: AgentMessageConfig[];
  threadState: ThreadState;
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
  default: { width: 170, height: 100 },
  end: { width: 120, height: 80 },
};

const getLayoutedElements = (
  nodes: Node[],
  edges: Edge[],
  direction: "TB" | "LR"
) => {
  const g = new Dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));

  // Updated graph settings
  g.setGraph({
    rankdir: direction,
    nodesep: 80,
    ranksep: 120,
    ranker: "tight-tree",
    marginx: 30,
    marginy: 30,
  });

  // Add nodes (unchanged)
  nodes.forEach((node) => {
    const dimensions =
      node.data.type === "end" ? NODE_DIMENSIONS.end : NODE_DIMENSIONS.default;
    g.setNode(node.id, { ...node, ...dimensions });
  });

  // Create a map to track bidirectional edges
  const bidirectionalPairs = new Map<
    string,
    { source: string; target: string }[]
  >();

  // First pass - identify bidirectional pairs
  edges.forEach((edge) => {
    const forwardKey = `${edge.source}->${edge.target}`;
    const reverseKey = `${edge.target}->${edge.source}`;
    const pairKey = [edge.source, edge.target].sort().join("-");

    if (!bidirectionalPairs.has(pairKey)) {
      bidirectionalPairs.set(pairKey, []);
    }
    bidirectionalPairs.get(pairKey)!.push({
      source: edge.source,
      target: edge.target,
    });
  });

  // Second pass - add edges with weights
  bidirectionalPairs.forEach((pairs, pairKey) => {
    if (pairs.length === 2) {
      // Bidirectional edge
      const [first, second] = pairs;
      g.setEdge(first.source, first.target, {
        weight: 2,
        minlen: 1,
      });
      g.setEdge(second.source, second.target, {
        weight: 1,
        minlen: 1,
      });
    } else {
      // Regular edge
      const edge = pairs[0];
      g.setEdge(edge.source, edge.target, {
        weight: 1,
        minlen: 1,
      });
    }
  });

  // Run layout
  Dagre.layout(g);

  // Position nodes
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

  // Process edges with positions
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
  const isStreamingOrWaiting =
    threadState?.status === "streaming" ||
    threadState?.status === "awaiting_input";
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
        draggable: !isStreamingOrWaiting,
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
        draggable: false,
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
      draggable: !isStreamingOrWaiting,
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
}) => {
  const { fitView } = useReactFlow();
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [shouldRefit, setShouldRefit] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  // Get settings from store
  const { agentFlow: settings, setAgentFlowSettings } = useConfigStore();

  const onNodesChange = useCallback((changes: NodeChange[]) => {
    setNodes((nds) => applyNodeChanges(changes, nds));
  }, []);
  const flowWrapper = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (shouldRefit) {
      const timeoutId = setTimeout(() => {
        fitView({ padding: 0.2, duration: 200 });
        setShouldRefit(false);
      }, 100); // Increased delay slightly

      return () => clearTimeout(timeoutId);
    }
  }, [shouldRefit, fitView]);

  // Process messages into nodes and edges
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

      // Helper function to create edge label based on settings
      const createEdgeLabel = (transition: MessageSequence) => {
        if (!settings.showLabels) return "";
        if (transition.totalTokens > 0) {
          return `${transition.count > 1 ? `${transition.count}x` : ""} ${
            settings.showTokens ? `(${transition.totalTokens} tokens)` : ""
          }`.trim();
        }
        return "";
      };

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
              label: createEdgeLabel(transition),
              messages: settings.showMessages ? transition.messages : [],
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
              label: createEdgeLabel(transition),
              messages: settings.showMessages ? transition.messages : [],
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
              label: settings.showLabels ? "ended" : "",
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
    [teamConfig.participants, threadState, settings]
  );

  const handleToggleFullscreen = useCallback(() => {
    setIsFullscreen(!isFullscreen);
    setShouldRefit(true);
  }, [isFullscreen]);

  useEffect(() => {
    if (!isFullscreen) return;

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        handleToggleFullscreen();
      }
    };

    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [isFullscreen, handleToggleFullscreen]);

  useEffect(() => {
    const { nodes: newNodes, edges: newEdges } = processMessages(messages);
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      newNodes,
      newEdges,
      settings.direction
    );

    setNodes(layoutedNodes);
    setEdges(layoutedEdges);

    if (messages.length > 0) {
      setTimeout(() => {
        fitView({ padding: 0.2, duration: 200 });
      }, 50);
    }
  }, [messages, processMessages, settings.direction, threadState, fitView]);

  // Define common ReactFlow props
  const reactFlowProps = {
    nodes,
    edges,
    nodeTypes,
    edgeTypes,
    defaultViewport: { x: 0, y: 0, zoom: 1 },
    minZoom: 0.5,
    maxZoom: 2,
    onNodesChange,
    proOptions: { hideAttribution: true },
  };

  // Define common toolbar props
  const toolbarProps = useMemo(
    () => ({
      isFullscreen,
      onToggleFullscreen: handleToggleFullscreen,
      onResetView: () => fitView({ padding: 0.2, duration: 200 }),
    }),
    [isFullscreen, handleToggleFullscreen, fitView]
  );
  return (
    <div
      ref={flowWrapper}
      className={`transition-all duration-200 ${
        isFullscreen
          ? "fixed inset-4 z-[9999] shadow" // Modal-like styling
          : "w-full h-full min-h-[300px]"
      } bg-tertiary rounded-lg`}
    >
      {/* Backdrop when fullscreen */}
      {isFullscreen && (
        <div
          className="fixed inset-0 -z-10 bg-background/80 backdrop-blur-sm"
          onClick={handleToggleFullscreen}
        />
      )}

      <ReactFlow {...reactFlowProps}>
        {settings.showGrid && <Background />}
        {/* <Controls /> */}
        <div className="absolute top-0 right-0 z-50">
          <AgentFlowToolbar {...toolbarProps} />
        </div>
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
