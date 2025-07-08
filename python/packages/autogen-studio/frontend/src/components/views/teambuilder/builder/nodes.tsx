import React, { memo } from "react";
import {
  Handle,
  Position,
  NodeProps,
  EdgeProps,
  getBezierPath,
  BaseEdge,
} from "@xyflow/react";
import {
  LucideIcon,
  Users,
  Wrench,
  Brain,
  Timer,
  Trash2Icon,
  Edit,
  Bot,
  Package,
} from "lucide-react";
import { CustomNode } from "./types";
import {
  AgentConfig,
  TeamConfig,
  WorkbenchConfig,
  StaticWorkbenchConfig,
  McpWorkbenchConfig,
  ComponentTypes,
  Component,
  ComponentConfig,
} from "../../../types/datamodel";
import { useDroppable } from "@dnd-kit/core";
import { TruncatableText } from "../../atoms";
import { useTeamBuilderStore } from "./store";
import {
  isAssistantAgent,
  isSelectorTeam,
  isSwarmTeam,
  isWebSurferAgent,
  isAnyStaticWorkbench,
  isMcpWorkbench,
} from "../../../types/guards";

// Icon mapping for different node types
export const iconMap: Record<
  Component<ComponentConfig>["component_type"],
  LucideIcon
> = {
  team: Users,
  agent: Bot,
  tool: Wrench,
  model: Brain,
  termination: Timer,
  workbench: Package,
};

interface DroppableZoneProps {
  accepts: ComponentTypes[];
  children?: React.ReactNode;
  className?: string;
  id: string; // Add this to make each zone uniquely identifiable
}

const DroppableZone = memo<DroppableZoneProps>(
  ({ accepts, children, className, id }) => {
    const { isOver, setNodeRef, active } = useDroppable({
      id,
      data: { accepts },
    });

    // Fix the data path to handle nested current objects
    const isValidDrop =
      isOver &&
      active?.data?.current?.current?.type &&
      accepts.includes(active.data.current.current.type);

    return (
      <div
        ref={setNodeRef}
        className={`droppable-zone p-2 ${isValidDrop ? "can-drop" : ""} ${
          className || ""
        }`}
      >
        {children}
      </div>
    );
  }
);
DroppableZone.displayName = "DroppableZone";

// Base node layout component
interface BaseNodeProps extends NodeProps<CustomNode> {
  id: string;
  icon: LucideIcon;
  children?: React.ReactNode;
  headerContent?: React.ReactNode;
  descriptionContent?: React.ReactNode;
  className?: string;
  onEditClick?: (id: string) => void;
}

const BaseNode = memo<BaseNodeProps>(
  ({
    id,
    data,
    selected,
    dragHandle,
    icon: Icon,
    children,
    headerContent,
    descriptionContent,
    className,
    onEditClick,
  }) => {
    const removeNode = useTeamBuilderStore((state) => state.removeNode);
    const setSelectedNode = useTeamBuilderStore(
      (state) => state.setSelectedNode
    );
    const showDelete = data.type !== "team";

    return (
      <div
        ref={dragHandle}
        className={`
        bg-white text-primary relative rounded-lg shadow-lg w-72 
        ${selected ? "ring-2 ring-accent" : ""}
        ${className || ""} 
        transition-all duration-200
      `}
      >
        <div className="border-b p-3 bg-gray-50 rounded-t-lg">
          <div className="flex items-center justify-between min-w-0">
            <div className="flex items-center gap-2 min-w-0 flex-1">
              <Icon className="flex-shrink-0 w-5 h-5 text-gray-600" />
              <span className="font-medium text-gray-800 truncate">
                {data.component.label}
              </span>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <span className="text-xs px-2 py-1 bg-gray-200 rounded text-gray-700">
                {data.component.component_type}
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedNode(id);
                }}
                className="p-1 hover:bg-secondary rounded"
              >
                <Edit className="w-4 h-4 text-accent" />
              </button>
              {showDelete && (
                <>
                  <button
                    onClick={(e) => {
                      console.log("remove node", id);
                      e.stopPropagation();
                      if (id) removeNode(id);
                    }}
                    className="p-1 hover:bg-red-100 rounded"
                  >
                    <Trash2Icon className="w-4 h-4 text-red-500" />
                  </button>
                </>
              )}
            </div>
          </div>
          {headerContent}
        </div>

        <div className="px-3 py-2 border-b text-sm text-gray-600">
          {descriptionContent}
        </div>

        <div className="p-3 space-y-2">{children}</div>
      </div>
    );
  }
);

BaseNode.displayName = "BaseNode";

// Reusable components
const NodeSection: React.FC<{
  title: string | React.ReactNode;
  children: React.ReactNode;
}> = ({ title, children }) => (
  <div className="space-y-1 relative">
    <h4 className="text-xs font-medium text-gray-500 uppercase">{title}</h4>
    <div className="bg-gray-50 rounded p-2">{children}</div>
  </div>
);

const ConnectionBadge: React.FC<{
  connected: boolean;
  label: string;
}> = ({ connected, label }) => (
  <span
    className={`
      text-xs px-2 py-1 rounded-full
      ${connected ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-600"}
    `}
  >
    {label}
  </span>
);

// Team Node
export const TeamNode = memo<NodeProps<CustomNode>>((props) => {
  const component = props.data.component as Component<TeamConfig>;
  const hasModel = isSelectorTeam(component) && !!component.config.model_client;
  const participantCount = component.config.participants?.length || 0;

  // Get team type label
  const teamType = isSwarmTeam(component)
    ? "Swarm"
    : isSelectorTeam(component)
    ? "Selector"
    : "RoundRobin";

  return (
    <BaseNode
      {...props}
      icon={iconMap.team}
      headerContent={
        <div className="flex gap-2 mt-2">
          <ConnectionBadge connected={true} label={teamType} />
          {isSelectorTeam(component) && (
            <ConnectionBadge connected={hasModel} label="Model" />
          )}
          <ConnectionBadge
            connected={participantCount > 0}
            label={`${participantCount} Agent${
              participantCount > 1 ? "s" : ""
            }`}
          />
        </div>
      }
      descriptionContent={
        <div>
          <div>
            <TruncatableText
              content={component.description || component.label || ""}
              textThreshold={150}
              showFullscreen={false}
            />
          </div>
          {isSelectorTeam(component) && component.config.selector_prompt && (
            <div className="mt-1 text-xs">
              Selector:{" "}
              <TruncatableText
                content={component.config.selector_prompt}
                textThreshold={150}
                showFullscreen={false}
              />
            </div>
          )}
          {isSwarmTeam(component) && (
            <div className="mt-1 text-xs text-gray-600">
              Handoff-based agent coordination
            </div>
          )}
        </div>
      }
    >
      {isSelectorTeam(component) && (
        <NodeSection title="Model">
          {/* <Handle
            type="target"
            position={Position.Left}
            id={`${props.id}-model-input-handle`}
            className="my-left-handle"
          /> */}

          <div className="relative">
            {hasModel && (
              <div className="text-sm">
                {component.config.model_client.config.model}
              </div>
            )}
            <DroppableZone id={`${props.id}@@@model-zone`} accepts={["model"]}>
              <div className="text-secondary text-xs my-1 text-center">
                Drop model here
              </div>
            </DroppableZone>
          </div>
        </NodeSection>
      )}

      <NodeSection
        title={
          <div>
            Agents{" "}
            <span className="text-xs text-accent">({participantCount})</span>
          </div>
        }
      >
        <Handle
          type="source"
          position={Position.Right}
          id={`${props.id}-agent-output-handle`}
          className="my-right-handle"
        />
        <div className="space-y-1">
          {component.config.participants?.map((participant, index) => (
            <div
              key={index}
              className="relative text-sm py-1 px-2 bg-white rounded flex items-center gap-2"
            >
              <Brain className="w-4 h-4 text-gray-500" />
              <span>{participant.config.name}</span>
            </div>
          ))}
          <DroppableZone id={`${props.id}@@@agent-zone`} accepts={["agent"]}>
            <div className="text-secondary text-xs my-1 text-center">
              Drop agents here
            </div>
          </DroppableZone>
        </div>
      </NodeSection>

      <NodeSection title="Terminations">
        {/* {
          <Handle
            type="target"
            position={Position.Left}
            id={`${props.id}-termination-input-handle`}
            className="my-left-handle"
          />
        } */}
        <div className="space-y-1">
          {component.config.termination_condition && (
            <div className="text-sm py-1 px-2 bg-white rounded flex items-center gap-2">
              <Timer className="w-4 h-4 text-gray-500" />
              <span>
                {component.config.termination_condition.label ||
                  component.config.termination_condition.component_type}
              </span>
            </div>
          )}
          <DroppableZone
            id={`${props.id}@@@termination-zone`}
            accepts={["termination"]}
          >
            <div className="text-secondary text-xs my-1 text-center">
              Drop termination here
            </div>
          </DroppableZone>
        </div>
      </NodeSection>
    </BaseNode>
  );
});

TeamNode.displayName = "TeamNode";

export const AgentNode = memo<NodeProps<CustomNode>>((props) => {
  const component = props.data.component as Component<AgentConfig>;
  const hasModel =
    isAssistantAgent(component) && !!component.config.model_client;

  // Get workbench info instead of direct tools
  const workbenchInfos = (() => {
    if (!isAssistantAgent(component)) return [];

    const workbenchConfig = component.config.workbench;
    if (!workbenchConfig) return [];

    // Handle both single workbench object and array of workbenches
    const workbenches = Array.isArray(workbenchConfig)
      ? workbenchConfig
      : [workbenchConfig];

    return workbenches.map((workbench) => {
      if (!workbench) {      return {
        hasWorkbench: false,
        toolCount: 0,
        workbenchType: "unknown" as const,
        serverType: null,
        workbench,
      };
      }

      if (isAnyStaticWorkbench(workbench)) {
        return {
          hasWorkbench: true,
          toolCount: (workbench as Component<StaticWorkbenchConfig>).config.tools?.length || 0,
          workbenchType: "static" as const,
          serverType: null,
          workbench,
        };
      } else if (isMcpWorkbench(workbench)) {
        const serverType = workbench.config.server_params?.type || "unknown";
        return {
          hasWorkbench: true,
          toolCount: 0,
          workbenchType: "mcp" as const,
          serverType: serverType,
          workbench,
        };
      }

      return {
        hasWorkbench: true,
        toolCount: 0,
        workbenchType: "unknown" as const,
        serverType: null,
        workbench,
      };
    });
  })();

  const totalToolCount = workbenchInfos.reduce(
    (sum, info) => sum + (info.workbenchType === "static" ? info.toolCount : 0),
    0
  );

  return (
    <BaseNode
      {...props}
      icon={iconMap.agent}
      headerContent={
        <div className="flex gap-2 mt-2">
          {isAssistantAgent(component) && (
            <>
              <ConnectionBadge connected={hasModel} label="Model" />
              <ConnectionBadge
                connected={workbenchInfos.length > 0}
                label={`${workbenchInfos.length} Workbench${
                  workbenchInfos.length !== 1 ? "es" : ""
                } (${totalToolCount} Tool${totalToolCount !== 1 ? "s" : ""})`}
              />
            </>
          )}
        </div>
      }
      descriptionContent={
        <div>
          <div className="break-words truncate mb-1">
            {" "}
            {component.config.name}
          </div>
          <div className="break-words"> {component.description}</div>
        </div>
      }
    >
      <Handle
        type="target"
        position={Position.Left}
        id={`${props.id}-agent-input-handle`}
        className="my-left-handle z-100"
      />

      {(isAssistantAgent(component) || isWebSurferAgent(component)) && (
        <>
          <NodeSection title="Model">
            <div className="relative">
              {component.config?.model_client && (
                <div className="text-sm">
                  {component.config?.model_client.config?.model}
                </div>
              )}
              <DroppableZone
                id={`${props.id}@@@model-zone`}
                accepts={["model"]}
              >
                <div className="text-secondary text-xs my-1 text-center">
                  Drop model here
                </div>
              </DroppableZone>
            </div>
          </NodeSection>

          {isAssistantAgent(component) && (
            <NodeSection title={`Workbenches (${workbenchInfos.length})`}>
              <Handle
                type="target"
                position={Position.Left}
                id={`${props.id}-workbench-input-handle`}
                className="my-left-handle"
              />
              <div className="space-y-3">
                {workbenchInfos.length > 0 ? (
                  workbenchInfos.map((workbenchInfo, index) => (
                    <div key={index} className="space-y-1">
                      <div className="text-sm py-1 px-2 bg-white rounded flex items-center gap-2">
                        <Package className="w-4 h-4 text-gray-500" />
                        <span>
                          {workbenchInfo.workbenchType === "static"
                            ? `Static Workbench (${
                                workbenchInfo.toolCount
                              } Tool${
                                workbenchInfo.toolCount !== 1 ? "s" : ""
                              })`
                            : workbenchInfo.workbenchType === "mcp"
                            ? `MCP Workbench (${workbenchInfo.serverType})`
                            : `Workbench (${(workbenchInfo.workbench as any)?.provider || "Unknown"})`}
                        </span>
                      </div>
                      {workbenchInfo.workbenchType === "static" &&
                        workbenchInfo.toolCount > 0 && (
                          <div className="ml-2">
                            {(
                              workbenchInfo.workbench as Component<StaticWorkbenchConfig>
                            ).config.tools.map((tool, toolIndex) => (
                              <div
                                key={toolIndex}
                                className="text-sm py-1 px-2 bg-white rounded flex items-center gap-2 mb-1"
                              >
                                <Wrench className="w-4 h-4 text-gray-500" />
                                <span className="truncate text-xs">
                                  {tool.config.name ||
                                    tool.label ||
                                    "Unnamed Tool"}
                                </span>
                              </div>
                            ))}
                          </div>
                        )}
                    </div>
                  ))
                ) : (
                  <div className="text-xs text-gray-500 text-center p-2">
                    No workbenches connected
                  </div>
                )}
                <DroppableZone
                  id={`${props.id}@@@workbench-zone`}
                  accepts={["workbench"]}
                >
                  <div className="text-secondary text-xs my-1 text-center">
                    Drop workbench here
                  </div>
                </DroppableZone>
              </div>
            </NodeSection>
          )}
        </>
      )}
    </BaseNode>
  );
});

AgentNode.displayName = "AgentNode";

// Workbench Node
export const WorkbenchNode = memo<NodeProps<CustomNode>>((props) => {
  const component = props.data.component as Component<WorkbenchConfig>;

  const workbenchInfo = (() => {
    if (isAnyStaticWorkbench(component)) {
      const toolCount = (component as Component<StaticWorkbenchConfig>).config.tools?.length || 0;
      return {
        type: "static" as const,
        toolCount,
        subtitle: `${toolCount} static tool${toolCount !== 1 ? "s" : ""}`,
        hasContent: toolCount > 0,
      };
    } else if (isMcpWorkbench(component)) {
      const serverType = component.config.server_params?.type || "unknown";
      return {
        type: "mcp" as const,
        toolCount: 0, // Dynamic - unknown count
        subtitle: `MCP Server (${serverType})`,
        hasContent: true,
      };
    }
    return {
      type: "unknown" as const,
      toolCount: 0,
      subtitle: "Unknown workbench type",
      hasContent: false,
    };
  })();

  return (
    <BaseNode
      {...props}
      icon={iconMap.workbench}
      headerContent={
        <div className="flex gap-2 mt-2">
          <ConnectionBadge
            connected={workbenchInfo.hasContent}
            label={workbenchInfo.subtitle}
          />
        </div>
      }
      descriptionContent={
        <div>
          <div className="break-words truncate mb-1">
            {component.description || "Workbench for managing tools"}
          </div>
        </div>
      }
    >
      <Handle
        type="source"
        position={Position.Right}
        id={`${props.id}-workbench-output-handle`}
        className="my-right-handle"
      />

      {/* Static Workbench Content */}
      {workbenchInfo.type === "static" && (
        <NodeSection title={`Tools (${workbenchInfo.toolCount})`}>
          <div className="space-y-1">
            {workbenchInfo.toolCount > 0 ? (
              (component as Component<StaticWorkbenchConfig>).config.tools.map(
                (tool, index) => (
                  <div
                    key={index}
                    className="text-sm py-1 px-2 bg-white rounded flex items-center gap-2"
                  >
                    <Wrench className="w-4 h-4 text-gray-500" />
                    <span className="truncate text-xs">
                      {tool.config.name || tool.label || "Unnamed Tool"}
                    </span>
                  </div>
                )
              )
            ) : (
              <div className="text-xs text-gray-500 text-center p-2">
                No tools configured
              </div>
            )}
            <DroppableZone id={`${props.id}@@@tool-zone`} accepts={["tool"]}>
              <div className="text-secondary text-xs my-1 text-center">
                Drop tool here
              </div>
            </DroppableZone>
          </div>
        </NodeSection>
      )}

      {/* MCP Workbench Content */}
      {workbenchInfo.type === "mcp" && (
        <NodeSection title="MCP Configuration">
          <div className="space-y-1">
            <div className="text-sm py-1 px-2 bg-white rounded flex items-center gap-2">
              <Package className="w-4 h-4 text-gray-500" />
              <span>Dynamic Tools</span>
            </div>
            <div className="text-xs text-gray-600 p-2">
              Tools provided by{" "}
              {
                (component as Component<McpWorkbenchConfig>).config
                  .server_params.type
              }{" "}
              server
            </div>
          </div>
        </NodeSection>
      )}
    </BaseNode>
  );
});

WorkbenchNode.displayName = "WorkbenchNode";

// Export all node types
export const nodeTypes = {
  team: TeamNode,
  agent: AgentNode,
  workbench: WorkbenchNode,
};

const EDGE_STYLES = {
  "model-connection": { stroke: "rgb(220,220,220)" },
  "tool-connection": { stroke: "rgb(220,220,220)" },
  "workbench-connection": { stroke: "rgb(34, 197, 94)" }, // Green for workbench connections
  "agent-connection": { stroke: "rgb(220,220,220)" },
  "termination-connection": { stroke: "rgb(220,220,220)" },
} as const;

type EdgeType = keyof typeof EDGE_STYLES;
type CustomEdgeProps = EdgeProps & {
  type: EdgeType;
};

export const CustomEdge = ({
  type,
  data,
  deletable,
  ...props
}: CustomEdgeProps) => {
  const [edgePath] = getBezierPath(props);
  const edgeType = type || "model-connection";

  // Extract only the SVG path properties we want to pass
  const { style: baseStyle, ...pathProps } = props;
  const {
    // Filter out the problematic props
    sourceX,
    sourceY,
    sourcePosition,
    targetPosition,
    sourceHandleId,
    targetHandleId,
    pathOptions,
    selectable,
    ...validPathProps
  } = pathProps;

  return (
    <BaseEdge
      path={edgePath}
      style={{ ...EDGE_STYLES[edgeType], strokeWidth: 2 }}
      {...validPathProps}
    />
  );
};

export const edgeTypes = {
  "model-connection": CustomEdge,
  "tool-connection": CustomEdge,
  "workbench-connection": CustomEdge,
  "agent-connection": CustomEdge,
  "termination-connection": CustomEdge,
};
