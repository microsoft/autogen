import React from "react";
import { Handle, Position, NodeProps, Node } from "@xyflow/react";
import { Bot, X } from "lucide-react";
import { NodeData } from "./types";

type StepNodeType = Node<NodeData>;

export const StepNode: React.FC<NodeProps<StepNodeType>> = ({
  data,
  selected,
  id,
}) => {
  const { step, onDelete } = data;

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

  return (
    <div
      className={`
      group relative w-[220px] bg-primary rounded-lg border-2 shadow-sm transition-all
      ${selected ? "border-accent shadow-lg" : "border-secondary"}
      cursor-pointer
    `}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!bg-accent !w-2 !h-5 !rounded-r-sm !-ml-1 !border-0 hover:!bg-accent/80 transition-colors"
      />
      <Handle
        type="source"
        position={Position.Right}
        className="!bg-accent !w-2 !h-5 !rounded-l-sm !-mr-1 !border-0 hover:!bg-accent/80 transition-colors"
      />

      <div className="p-3">
        <div className="flex items-center gap-2 mb-2">
          <Bot className="w-4 h-4 text-accent flex-shrink-0" />
          <span
            className="font-medium text-sm truncate flex-1 text-primary"
            title={step.name}
          >
            {step.name}
          </span>
          <button
            onClick={handleDelete}
            className="opacity-0 group-hover:opacity-100 transition-opacity text-secondary hover:text-red-500"
            aria-label="Delete step"
          >
            <X size={14} />
          </button>
        </div>

        <div
          className="text-xs text-secondary mb-2 overflow-hidden"
          style={{
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
            height: "2rem",
            lineHeight: "1rem",
          }}
          title={step.description}
        >
          {step.description}
        </div>

        <div className="flex items-center gap-2 text-xs">
          <span className="px-1.5 py-0.5 bg-accent/10 text-accent rounded text-xs truncate flex-1">
            {step.model || "Not specified"}
          </span>

          {step.tools && step.tools.length > 0 && (
            <span className="px-1.5 py-0.5 bg-secondary/50 text-secondary rounded text-xs">
              {step.tools.length} tools
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
