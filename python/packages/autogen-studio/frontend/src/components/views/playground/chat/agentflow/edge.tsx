import React from "react";
import { AgentMessageConfig } from "../../../../types/datamodel";
import {
  Edge,
  EdgeLabelRenderer,
  type EdgeProps,
  getSmoothStepPath,
} from "@xyflow/react";

export interface CustomEdgeData extends Record<string, unknown> {
  label?: string;
  messages: AgentMessageConfig[];
  routingType?: "primary" | "secondary";
  bidirectionalPair?: string;
  onClick?: () => void;
}

export type CustomEdge = Edge<CustomEdgeData>;

interface CustomEdgeProps extends Omit<EdgeProps, "data"> {
  data: CustomEdgeData;
}

export const CustomEdge: React.FC<CustomEdgeProps> = ({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  source,
  target,
  data,
  style = {},
  markerEnd,
}) => {
  const isSelfLoop = source === target;

  // Keep stroke width scaling for message count but with a cleaner implementation
  const baseStrokeWidth = (style.strokeWidth as number) || 1;
  const messageCount = data.messages?.length || 0;
  const finalStrokeWidth = isSelfLoop
    ? Math.max(baseStrokeWidth, 2)
    : Math.min(Math.max(messageCount, 1), 5) * baseStrokeWidth;

  let edgePath = "";
  let labelX = 0;
  let labelY = 0;

  if (isSelfLoop) {
    const rightOffset = 160;
    const verticalOffset = sourceY - targetY;
    const verticalPadding = 6;
    const radius = 8;

    edgePath = `
     M ${sourceX} ${targetY - verticalPadding}
     L ${sourceX + rightOffset - radius} ${targetY - verticalPadding}
     Q ${sourceX + rightOffset} ${targetY - verticalPadding} ${
      sourceX + rightOffset
    } ${targetY - verticalPadding + radius}
     L ${sourceX + rightOffset} ${sourceY + verticalPadding - radius}
     Q ${sourceX + rightOffset} ${sourceY + verticalPadding} ${
      sourceX + rightOffset - radius
    } ${sourceY + verticalPadding}
     L ${sourceX} ${sourceY + verticalPadding}
   `;

    labelX = sourceX + rightOffset + 10;
    labelY = targetY + verticalOffset / 2;
  } else {
    [edgePath, labelX, labelY] = getSmoothStepPath({
      sourceX,
      sourceY,
      targetX,
      targetY,
    });
  }

  // Calculate label position with offset for bidirectional edges
  const getLabelPosition = (x: number, y: number) => {
    if (!data.routingType || isSelfLoop) return { x, y };

    // Make vertical separation more pronounced
    const verticalOffset = data.routingType === "secondary" ? -35 : 35;
    const horizontalOffset = data.routingType === "secondary" ? -25 : 25;

    // Calculate edge angle to determine if it's more horizontal or vertical
    const dx = targetX - sourceX;
    const dy = targetY - sourceY;
    const isMoreHorizontal = Math.abs(dx) > Math.abs(dy);

    // Always apply some vertical offset
    const basePosition = {
      x: isMoreHorizontal ? x : x + horizontalOffset,
      y: y + (data.routingType === "secondary" ? -20 : 20),
    };

    return basePosition;
  };

  const labelPosition = getLabelPosition(labelX, labelY);

  return (
    <>
      <path
        id={id}
        className="react-flow__edge-path"
        d={edgePath}
        style={{
          ...style,
          strokeWidth: finalStrokeWidth,
          stroke: data.routingType === "secondary" ? "#0891b2" : style.stroke,
        }}
        markerEnd={markerEnd}
      />
      {data?.label && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: "absolute",
              transform: `translate(-50%, -50%) translate(${labelPosition.x}px,${labelPosition.y}px)`,
              pointerEvents: "all",
              transition: "all 0.2s ease-in-out",
            }}
            onClick={data.onClick}
          >
            <div
              className="px-2 py-1 rounded bg-secondary hover:bg-tertiary text-primary  
                       cursor-pointer transform hover:scale-110 transition-all
                       flex items-center gap-1"
              style={{
                whiteSpace: "nowrap",
              }}
            >
              {messageCount > 0 && (
                <span className="text-xs text-secondary">({messageCount})</span>
              )}
              <span className="text-sm">{data.label}</span>
            </div>
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
};
