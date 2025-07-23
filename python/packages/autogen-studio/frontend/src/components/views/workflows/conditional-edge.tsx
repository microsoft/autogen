import React from "react";
import {
  Edge,
  EdgeLabelRenderer,
  type EdgeProps,
  getBezierPath,
} from "@xyflow/react";
import { EdgeCondition } from "./types";
import { formatConditionLabel, getConditionTypeColor } from "./utils";

export interface ConditionalEdgeData extends Record<string, unknown> {
  condition?: EdgeCondition;
  onClick?: () => void;
}

export type ConditionalEdge = Edge<ConditionalEdgeData>;

interface ConditionalEdgeProps extends Omit<EdgeProps, "data"> {
  data?: ConditionalEdgeData;
}

export const ConditionalEdge: React.FC<ConditionalEdgeProps> = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  style = {},
  markerEnd,
}) => {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const condition = data?.condition;
  const label = formatConditionLabel(condition);
  const colorClass = getConditionTypeColor(condition);

  return (
    <>
      <path
        id={id}
        className="react-flow__edge-path"
        d={edgePath}
        style={style}
        markerEnd={markerEnd}
      />
      {label && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: "absolute",
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              pointerEvents: "all",
              transition: "all 0.2s ease-in-out",
            }}
            onClick={data?.onClick}
          >
            <div
              className={`px-2 py-1 rounded-md bg-white border shadow-sm text-xs font-medium
                       cursor-pointer transform hover:scale-105 transition-all
                       ${colorClass} border-gray-200 hover:border-gray-300`}
              style={{
                whiteSpace: "nowrap",
                fontSize: "11px",
              }}
            >
              {label}
            </div>
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
};