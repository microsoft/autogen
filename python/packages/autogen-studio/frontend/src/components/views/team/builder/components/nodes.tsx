import React from "react";
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
  Settings,
  Brain,
  Timer,
  Trash2Icon,
  Edit,
} from "lucide-react";
import { NodeData, CustomNode } from "../types";
import {
  AgentConfig,
  TeamConfigTypes,
  ModelConfigTypes,
  ToolConfig,
  TerminationConfigTypes,
  ComponentTypes,
} from "../../../../types/datamodel";
import { useDroppable } from "@dnd-kit/core";
import { TruncatableText } from "../../../atoms";
import { useTeamBuilderStore } from "../store";

// Icon mapping for different node types
const iconMap: Record<NodeData["type"], LucideIcon> = {
  team: Users,
  agent: Brain,
  tool: Wrench,
  model: Settings,
  termination: Timer,
};

interface DroppableZoneProps {
  accepts: ComponentTypes[];
  children?: React.ReactNode;
  className?: string;
  id: string; // Add this to make each zone uniquely identifiable
}

const DroppableZone: React.FC<DroppableZoneProps> = ({
  accepts,
  children,
  className,
  id,
}) => {
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
};

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

const BaseNode: React.FC<BaseNodeProps> = ({
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
  const setSelectedNode = useTeamBuilderStore((state) => state.setSelectedNode);
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
              {data.label}
            </span>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <span className="text-xs px-2 py-1 bg-gray-200 rounded text-gray-700">
              {data.type}
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

      {descriptionContent && (
        <div className="px-3 py-2 border-b text-sm text-gray-600">
          {descriptionContent}
        </div>
      )}

      <div className="p-3 space-y-2">{children}</div>
    </div>
  );
};

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
export const TeamNode: React.FC<NodeProps<CustomNode>> = (props) => {
  const config = props.data.config as TeamConfigTypes;
  const hasModel =
    config.team_type === "SelectorGroupChat" && !!config.model_client;
  const participantCount = config.participants?.length || 0;

  return (
    <BaseNode
      {...props}
      icon={iconMap.team}
      headerContent={
        <div className="flex gap-2 mt-2">
          <ConnectionBadge connected={hasModel} label="Model" />
          <ConnectionBadge
            connected={participantCount > 0}
            label={`${participantCount} Agent ${
              participantCount > 1 ? "s" : ""
            }`}
          />
        </div>
      }
      descriptionContent={
        <div>
          <div>Type: {config.team_type}</div>
          {config.team_type === "SelectorGroupChat" &&
            config.selector_prompt && (
              <div className="mt-1 text-xs">
                Selector:{" "}
                <TruncatableText
                  content={config.selector_prompt}
                  textThreshold={150}
                />
              </div>
            )}
        </div>
      }
    >
      {config.team_type === "SelectorGroupChat" && (
        <NodeSection title="Model">
          <Handle
            type="target"
            position={Position.Left}
            id={`${props.id}-model-input-handle`}
            className="my-left-handle"
          />

          <div className="relative">
            {hasModel && (
              <div className="text-sm">{config.model_client.model}</div>
            )}
            <DroppableZone id={`${props.id}-model-zone`} accepts={["model"]}>
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
        {true && (
          <Handle
            type="source"
            position={Position.Right}
            id={`${props.id}-agent-output-handle`}
            className="my-right-handle"
          />
        )}
        <div className="space-y-1">
          {config.participants?.map((participant, index) => (
            <div
              key={index}
              className="relative text-sm py-1 px-2 bg-white rounded flex items-center gap-2"
            >
              <Brain className="w-4 h-4 text-gray-500" />
              <span>{participant.name}</span>
            </div>
          ))}
          <DroppableZone id={`${props.id}-agent-zone`} accepts={["agent"]}>
            <div className="text-secondary text-xs my-1 text-center">
              Drop agents here
            </div>
          </DroppableZone>
        </div>
      </NodeSection>

      <NodeSection title="Terminations">
        {config.termination_condition && (
          <Handle
            type="target"
            position={Position.Left}
            id={`${props.id}-termination-input-handle`}
            className="my-left-handle"
          />
        )}
        <div className="space-y-1">
          {config.termination_condition && (
            <div className="text-sm py-1 px-2 bg-white rounded flex items-center gap-2">
              <Timer className="w-4 h-4 text-gray-500" />
              <span>{config.termination_condition.termination_type}</span>
            </div>
          )}
          <DroppableZone
            id={`${props.id}-termination-zone`}
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
};

export const AgentNode: React.FC<NodeProps<CustomNode>> = (props) => {
  const config = props.data.config as AgentConfig;
  const hasModel = !!config.model_client;
  const toolCount = config.tools?.length || 0;

  return (
    <BaseNode
      {...props}
      icon={iconMap.agent}
      headerContent={
        <div className="flex gap-2 mt-2">
          <ConnectionBadge connected={hasModel} label="Model" />
          <ConnectionBadge
            connected={toolCount > 0}
            label={`${toolCount} Tools`}
          />
        </div>
      }
      descriptionContent={
        <div>
          <div>Type: {config.agent_type}</div>
          {config.system_message && (
            <div className="mt-1 text-xs">
              <TruncatableText
                content={config.system_message}
                textThreshold={150}
              />
            </div>
          )}
        </div>
      }
    >
      <Handle
        type="target"
        position={Position.Left}
        id={`${props.id}-agent-input-handle`}
        className="my-left-handle"
      />

      <NodeSection title="Model">
        <Handle
          type="target"
          position={Position.Left}
          id={`${props.id}-model-input-handle`}
          className="my-left-handle"
        />

        <div className="relative">
          {config.model_client && (
            <>
              {" "}
              <div className="text-sm">{config.model_client.model}</div>
            </>
          )}
          <DroppableZone id={`${props.id}-model-zone`} accepts={["model"]}>
            <div className="text-secondary text-xs my-1 text-center">
              Drop model here
            </div>
          </DroppableZone>
        </div>
      </NodeSection>

      <NodeSection title="Tools">
        {
          <Handle
            type="target"
            position={Position.Left}
            id={`${props.id}-tool-input-handle`}
            className="my-left-handle"
          />
        }
        <div className="space-y-1">
          {config.tools && toolCount > 0 && (
            <div className="space-y-1">
              {config.tools.map((tool, index) => (
                <div
                  key={index}
                  className="relative text-sm py-1 px-2 bg-white rounded flex items-center gap-2"
                >
                  <Wrench className="w-4 h-4 text-gray-500" />
                  <span>{tool.name}</span>
                </div>
              ))}
            </div>
          )}
          <DroppableZone id={`${props.id}-tool-zone`} accepts={["tool"]}>
            <div className="text-secondary text-xs my-1 text-center">
              Drop tools here
            </div>
          </DroppableZone>
        </div>
      </NodeSection>
    </BaseNode>
  );
};

// Model Node
export const ModelNode: React.FC<NodeProps<CustomNode>> = (props) => {
  const config = props.data.config as ModelConfigTypes;

  return (
    <BaseNode
      {...props}
      icon={iconMap.model}
      descriptionContent={
        <div>
          <div>Type: {config.model_type}</div>
          {config.base_url && (
            <div className="mt-1 text-xs">URL: {config.base_url}</div>
          )}
        </div>
      }
    >
      <Handle
        type="source" // This model's handle should be source since it connects TO team/agent
        position={Position.Right}
        id={`${props.id}-model-output-handle`}
        className="my-right-handle"
      />
      <NodeSection title="Configuration">
        <div className="text-sm">Model: {config.model}</div>
      </NodeSection>
    </BaseNode>
  );
};

// Tool Node
export const ToolNode: React.FC<NodeProps<CustomNode>> = (props) => {
  const config = props.data.config as ToolConfig;

  return (
    <BaseNode
      {...props}
      icon={iconMap.tool}
      descriptionContent={<div>Tool Type: {config.tool_type}</div>}
    >
      <Handle
        type="source"
        position={Position.Right}
        id={`${props.id}-tool-output-handle`} // Add index to match store logic
        className="my-right-handle"
      />
      <NodeSection title="Configuration">
        <div className="text-sm">{config.description}</div>
      </NodeSection>

      <NodeSection title="Content">
        <div className="text-sm break-all">
          <TruncatableText content={config.content || ""} textThreshold={150} />
        </div>
      </NodeSection>
    </BaseNode>
  );
};

// Termination Node

// First, let's add the Termination Node component
export const TerminationNode: React.FC<NodeProps<CustomNode>> = (props) => {
  const config = props.data.config as TerminationConfigTypes;

  return (
    <BaseNode
      {...props}
      icon={iconMap.termination}
      descriptionContent={<div>Type: {config.termination_type}</div>}
    >
      <Handle
        type="source"
        position={Position.Right}
        id={`${props.id}-termination-output-handle`}
        className="my-right-handle"
      />

      <NodeSection title="Configuration">
        <div className="text-sm">
          {config.termination_type === "MaxMessageTermination" && (
            <div>Max Messages: {config.max_messages}</div>
          )}
          {config.termination_type === "TextMentionTermination" && (
            <div>Text: {config.text}</div>
          )}
        </div>
      </NodeSection>
    </BaseNode>
  );
};

// Export all node types
export const nodeTypes = {
  team: TeamNode,
  agent: AgentNode,
  model: ModelNode,
  tool: ToolNode,
  termination: TerminationNode,
};

const EDGE_STYLES = {
  "model-connection": { stroke: "rgb(59, 130, 246)" },
  "tool-connection": { stroke: "rgb(34, 197, 94)" },
  "agent-connection": { stroke: "rgb(168, 85, 247)" },
  "termination-connection": { stroke: "rgb(255, 159, 67)" },
} as const;

type EdgeType = keyof typeof EDGE_STYLES;

export const CustomEdge = ({ data, ...props }: EdgeProps) => {
  const [edgePath] = getBezierPath(props);
  const edgeType = (data?.type as EdgeType) || "model-connection";

  return (
    <BaseEdge
      path={edgePath}
      style={{ ...EDGE_STYLES[edgeType], strokeWidth: 2 }}
      {...props}
    />
  );
};

export const edgeTypes = {
  "model-connection": CustomEdge,
  "tool-connection": CustomEdge,
  "agent-connection": CustomEdge,
  "termination-connection": CustomEdge,
};
