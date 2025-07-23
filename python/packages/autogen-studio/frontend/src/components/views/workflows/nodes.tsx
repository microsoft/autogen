import React from "react";
import { Handle, Position, NodeProps, Node } from "@xyflow/react";
import {
  Bot,
  X,
  Play,
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
  AlertCircle,
  Expand,
  PlayCircle,
  StopCircle,
} from "lucide-react";
import { NodeData, StepStatus } from "./types";

type StepNodeType = Node<NodeData>;

// Helper function to get step status configuration
const getStepStatusConfig = (status: StepStatus) => {
  switch (status) {
    case StepStatus.RUNNING:
      return {
        icon: Loader2,
        text: "Running",
        color: "text-blue-500",
        bgColor: "bg-blue-50",
        borderColor: "border-blue-200",
        animate: "animate-spin",
      };
    case StepStatus.COMPLETED:
      return {
        icon: CheckCircle,
        text: "Completed",
        color: "text-green-500",
        bgColor: "bg-green-50",
        borderColor: "border-green-200",
        animate: "",
      };
    case StepStatus.FAILED:
      return {
        icon: XCircle,
        text: "Failed",
        color: "text-red-500",
        bgColor: "bg-red-50",
        borderColor: "border-red-200",
        animate: "",
      };
    case StepStatus.CANCELLED:
      return {
        icon: AlertCircle,
        text: "Cancelled",
        color: "text-orange-500",
        bgColor: "bg-orange-50",
        borderColor: "border-orange-200",
        animate: "",
      };
    case StepStatus.SKIPPED:
      return {
        icon: AlertCircle,
        text: "Skipped",
        color: "text-orange-500",
        bgColor: "bg-orange-50",
        borderColor: "border-orange-200",
        animate: "",
      };
    case StepStatus.PENDING:
    default:
      return {
        icon: Clock,
        text: "Pending",
        color: "text-gray-500",
        bgColor: "bg-gray-50",
        borderColor: "border-gray-200",
        animate: "",
      };
  }
};

export const StepNode: React.FC<NodeProps<StepNodeType>> = ({
  data,
  selected,
  id,
}) => {
  const { step, onDelete, executionStatus, executionData, onStepClick, workflowConfig } = data;

  if (!step) {
    return (
      <div className="p-4 border border-red-500 bg-red-50 rounded">
        <div className="text-red-600">Error: Step data not found</div>
      </div>
    );
  }

  const handleDelete = (e: React.MouseEvent) => {
    e.stopPropagation();
    onDelete?.(id);
  };

  const handleExpand = (e: React.MouseEvent) => {
    e.stopPropagation();
    onStepClick?.(step, executionData);
  };

  // Get status configuration - show no status if executionStatus is undefined (pre-run)
  const statusConfig = executionStatus
    ? getStepStatusConfig(executionStatus)
    : null;
  const IconComponent = statusConfig?.icon;

  // Determine if this is a start or end node
  const isStartNode = workflowConfig?.start_step_id === step.step_id;
  const isEndNode = workflowConfig?.end_step_ids?.includes(step.step_id);

  // Get appropriate node icon based on node type
  const getNodeIcon = () => {
    if (isStartNode) return PlayCircle;
    if (isEndNode) return StopCircle;
    return Bot;
  };
  
  const NodeIcon = getNodeIcon();

  return (
    <div
      className={`
      group relative w-[220px] bg-primary rounded-lg border-2 shadow-sm transition-all
      ${selected ? "border-accent shadow-lg" : "border-secondary"}
      cursor-pointer
    `}
    >
      {/* Only show target handle if not a start node */}
      {!isStartNode && (
        <Handle
          type="target"
          position={Position.Left}
          className="!bg-accent !w-2 !h-5 !rounded-r-sm !-ml-1 !border-0 hover:!bg-accent/80 transition-colors"
        />
      )}
      
      {/* Only show source handle if not an end node */}
      {!isEndNode && (
        <Handle
          type="source"
          position={Position.Right}
          className="!bg-accent !w-2 !h-5 !rounded-l-sm !-mr-1 !border-0 hover:!bg-accent/80 transition-colors"
        />
      )}

      <div className="p-3">
        {/* Header with step info and action buttons */}
        <div className="flex items-center gap-2 mb-2">
          <NodeIcon className={`w-4 h-4 flex-shrink-0 ${
            isStartNode ? "text-green-500" : isEndNode ? "text-red-500" : "text-accent"
          }`} />
          <span
            className="font-medium text-sm truncate flex-1 text-primary"
            title={step.metadata.name}
          >
            {isStartNode && "[START] "}{isEndNode && "[END] "}{step.metadata.name}
          </span>
          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={handleExpand}
              className="text-secondary hover:text-accent"
              aria-label="View step details"
            >
              <Expand size={14} />
            </button>
            <button
              onClick={handleDelete}
              className="text-secondary hover:text-red-500"
              aria-label="Delete step"
            >
              <X size={14} />
            </button>
          </div>
        </div>

        {/* Description */}
        {step.metadata.description && (
          <div
            className="text-xs text-secondary mb-3 overflow-hidden"
            style={{
              display: "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
              height: "2rem",
              lineHeight: "1rem",
            }}
            title={step.metadata.description}
          >
            {step.metadata.description}
          </div>
        )}

        {/* Status Indicator Section - Only show if there's a status */}
        {statusConfig && (
          <div className="border-t border-secondary pt-2">
            <div
              className={`flex items-center gap-2 px-2 py-1.5 rounded-md border text-xs font-medium ${statusConfig.bgColor} ${statusConfig.borderColor}`}
            >
              {IconComponent && (
                <IconComponent
                  size={12}
                  className={`${statusConfig.color} ${statusConfig.animate}`}
                />
              )}
              <span className={statusConfig.color}>{statusConfig.text}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
