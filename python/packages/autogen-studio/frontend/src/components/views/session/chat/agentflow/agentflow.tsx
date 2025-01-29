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
  NodeTypes,
  useReactFlow,
  ReactFlowProvider,
  NodeChange,
  applyNodeChanges,
  MiniMap,
} from "@xyflow/react";
import Dagre from "@dagrejs/dagre";
import "@xyflow/react/dist/style.css";
import AgentNode from "./agentnode";
import {
  AgentMessageConfig,
  AgentConfig,
  TeamConfig,
  Run,
  Component,
} from "../../../../types/datamodel";
import { CustomEdge, CustomEdgeData } from "./edge";
import { useConfigStore } from "../../../../../hooks/store";
import { AgentFlowToolbar } from "./toolbar";
import { EdgeMessageModal } from "./edgemessagemodal";

interface AgentFlowProps {
  teamConfig: Component<TeamConfig>;
  run: Run;
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
  end: { width: 170, height: 80 },
  task: { width: 170, height: 100 },
};

const getLayoutedElements = (
  nodes: Node[],
  edges: CustomEdge[],
  direction: "TB" | "LR"
) => {
  const g = new Dagre.graphlib.Graph().setDefaultEdgeLabel(() => ({}));

  g.setGraph({
    rankdir: direction,
    nodesep: 110,
    ranksep: 100,
    ranker: "network-simplex",
    marginx: 30,
    marginy: 30,
  });

  nodes.forEach((node) => {
    const dimensions =
      node.data.type === "end" ? NODE_DIMENSIONS.end : NODE_DIMENSIONS.default;
    g.setNode(node.id, { ...node, ...dimensions });
  });

  const bidirectionalPairs = new Map<
    string,
    { source: string; target: string }[]
  >();

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

  bidirectionalPairs.forEach((pairs, pairKey) => {
    if (pairs.length === 2) {
      const [first, second] = pairs;
      g.setEdge(first.source, first.target, { weight: 2, minlen: 1 });
      g.setEdge(second.source, second.target, { weight: 1, minlen: 1 });
    } else {
      const edge = pairs[0];
      g.setEdge(edge.source, edge.target, { weight: 1, minlen: 1 });
    }
  });

  Dagre.layout(g);

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

  const nodePositions = new Map(
    positionedNodes.map((node) => [
      node.id,
      {
        x: node.position.x + NODE_DIMENSIONS.default.width / 2,
        y: node.position.y + NODE_DIMENSIONS.default.height / 2,
      },
    ])
  );

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

  return { nodes: positionedNodes, edges: positionedEdges };
};

const createNode = (
  id: string,
  type: "user" | "agent" | "end",
  agentConfig?: Component<AgentConfig>,
  isActive: boolean = false,
  run?: Run
): Node => {
  const isProcessing =
    run?.status === "active" || run?.status === "awaiting_input";

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
        draggable: !isProcessing,
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
        status: run?.status,
        reason: run?.error_message || "",
        agentType: "",
        description: "",
        isActive: false,
        draggable: false,
      },
    };
  }

  // if (type === "task") {
  //   return {
  //     id,
  //     type: "agentNode",
  //     position: { x: 0, y: 0 },
  //     data: {
  //       type: "task",
  //       label: "Task",
  //       description: run?.task.content || "",
  //       isActive: false,
  //       status: null,
  //       reason: null,
  //       draggable: false,
  //     },
  //   };
  // }

  return {
    id,
    type: "agentNode",
    position: { x: 0, y: 0 },
    data: {
      type: "agent",
      label: id,
      agentType: agentConfig?.label || "",
      description: agentConfig?.description || "",
      isActive,
      status: "",
      reason: "",
      draggable: !isProcessing,
    },
  };
};

const nodeTypes: NodeTypes = {
  agentNode: AgentNode,
};

const edgeTypes = {
  custom: CustomEdge,
};

const AgentFlow: React.FC<AgentFlowProps> = ({ teamConfig, run }) => {
  const { fitView } = useReactFlow();
  const [nodes, setNodes] = useState<Node[]>([]);
  const [edges, setEdges] = useState<CustomEdge[]>([]);
  const [shouldRefit, setShouldRefit] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);

  const { agentFlow: settings } = useConfigStore();
  const [modalOpen, setModalOpen] = useState(false);
  const [selectedEdge, setSelectedEdge] = useState<CustomEdge | null>(null);

  const handleEdgeClick = useCallback((edge: CustomEdge) => {
    if (!edge.data?.messages) return; // Early return if no data/messages

    setSelectedEdge(edge);
    setModalOpen(true);
  }, []);

  const onNodesChange = useCallback((changes: NodeChange[]) => {
    setNodes((nds) => applyNodeChanges(changes, nds));
  }, []);

  const flowWrapper = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (shouldRefit) {
      const timeoutId = setTimeout(() => {
        fitView({ padding: 0.2, duration: 200 });
        setShouldRefit(false);
      }, 100);

      return () => clearTimeout(timeoutId);
    }
  }, [shouldRefit, fitView]);

  const processMessages = useCallback(
    (messages: AgentMessageConfig[]) => {
      if (!run.task) return { nodes: [], edges: [] };

      const nodeMap = new Map<string, Node>();
      const transitionCounts = new Map<string, MessageSequence>();
      const bidirectionalPatterns = new Map<string, BidirectionalPattern>();

      // Add first message node if it exists
      if (messages.length > 0) {
        const firstAgentConfig = teamConfig.config.participants.find(
          (p) => p.config.name === messages[0].source
        );
        nodeMap.set(
          messages[0].source,
          createNode(
            messages[0].source,
            messages[0].source === "user" ? "user" : "agent",
            firstAgentConfig,
            false,
            run
          )
        );
      }

      // Process message transitions
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

        if (!nodeMap.has(nextMsg.source)) {
          const agentConfig = teamConfig.config.participants.find(
            (p) => p.config.name === nextMsg.source
          );
          nodeMap.set(
            nextMsg.source,
            createNode(
              nextMsg.source,
              nextMsg.source === "user" ? "user" : "agent",
              agentConfig,
              false,
              run
            )
          );
        }
      }

      // Process bidirectional patterns
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
      const newEdges: CustomEdge[] = [];
      const processedKeys = new Set<string>();

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
          const forwardKey = `${source}->${target}`;
          const reverseKey = `${target}->${source}`;

          const forwardEdgeId = `${source}-${target}-forward`;
          const reverseEdgeId = `${target}-${source}-reverse`;

          const createBidirectionalEdge = (
            transition: MessageSequence,
            isSecondary: boolean,
            edgeId: string,
            pairedEdgeId: string
          ): CustomEdge => ({
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
              run.status === "active" &&
              key === Array.from(transitionCounts.keys()).pop(),
            style: {
              stroke: "#2563eb",
              strokeWidth: 1,
            },
          });
        }
      });

      // Add end node if run is complete/error/stopped
      if (run && messages.length > 0) {
        const lastMessage = messages[messages.length - 1];

        if (["complete", "error", "stopped"].includes(run.status)) {
          nodeMap.set("end", createNode("end", "end", undefined, false, run));

          const edgeColor = {
            complete: "#2563eb",
            stopped: "red",
            error: "red",
            active: "#2563eb",
            awaiting_input: "#2563eb",
            timeout: "red",
            created: "#2563eb",
          }[run.status];

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

      return { nodes: Array.from(nodeMap.values()), edges: newEdges };
    },
    [teamConfig.config.participants, run, settings]
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
    const { nodes: newNodes, edges: newEdges } = processMessages(
      run.messages.map((m) => m.config)
    );
    const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
      newNodes,
      newEdges,
      settings.direction
    );

    setNodes(layoutedNodes);
    setEdges(layoutedEdges);

    if (run.messages.length > 0) {
      setTimeout(() => {
        fitView({ padding: 0.2, duration: 200 });
      }, 50);
    }
  }, [run.messages, processMessages, settings.direction, run.status, fitView]);

  const reactFlowProps = {
    nodes,
    edges: edges.map((edge) => ({
      ...edge,
      data: {
        ...edge.data,
        onClick: () => handleEdgeClick(edge),
      },
    })),
    nodeTypes,
    edgeTypes,
    defaultViewport: { x: 0, y: 0, zoom: 1 },
    minZoom: 0.5,
    maxZoom: 2,
    onNodesChange,
    proOptions: { hideAttribution: true },
  };

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
          ? "fixed inset-4 z-[50] shadow"
          : "w-full h-full min-h-[300px]"
      } bg-tertiary rounded-lg`}
    >
      {isFullscreen && (
        <div
          className="fixed inset-0 -z-10 bg-background/80 backdrop-blur-sm"
          onClick={handleToggleFullscreen}
        />
      )}

      <ReactFlow {...reactFlowProps}>
        {settings.showGrid && <Background />}
        {settings.showMiniMap && <MiniMap />}
        <div className="absolute top-0 right-0 z-50">
          <AgentFlowToolbar {...toolbarProps} />
        </div>
      </ReactFlow>
      <EdgeMessageModal
        open={modalOpen}
        onClose={() => {
          setModalOpen(false);
          setSelectedEdge(null);
        }}
        edge={selectedEdge}
      />
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
