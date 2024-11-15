import React from "react";
import { Tooltip } from "antd";
import { AgentMessageConfig } from "../../../../types/datamodel";
import {
  EdgeLabelRenderer,
  type EdgeProps,
  getSmoothStepPath,
} from "@xyflow/react";
import { RenderMessage } from "../rendermessage";

interface EdgeTooltipContentProps {
  messages: AgentMessageConfig[];
}

interface CustomEdgeData {
  label?: string;
  messages: AgentMessageConfig[];
}

const EdgeTooltipContent: React.FC<EdgeTooltipContentProps> = ({
  messages,
}) => {
  return (
    <div className="p-2 overflow-auto max-h-[200px] scroll max-w-[350px]">
      <div className="text-xs mb-2">{messages.length} messages</div>
      <div className="edge-tooltip">
        {messages.map((message, index) => (
          <RenderMessage key={index} message={message} />
        ))}
      </div>
    </div>
  );
};

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
    const rightOffset = 120;
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

  return (
    <>
      <path
        id={id}
        className="react-flow__edge-path"
        d={edgePath}
        style={{
          ...style,
          strokeWidth: finalStrokeWidth,
        }}
        markerEnd={markerEnd}
      />
      {data?.label && (
        <EdgeLabelRenderer>
          <div
            style={{
              position: "absolute",
              transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
              pointerEvents: "all",
            }}
          >
            <Tooltip
              title={
                data.messages && data.messages.length > 0 ? (
                  <EdgeTooltipContent messages={data.messages} />
                ) : (
                  data?.label
                )
              }
              overlayStyle={{ maxWidth: "none" }}
            >
              <div className="px-2 py-1 rounded bg-secondary bg-opacity-50 text-primary text-sm">
                {data.label}
              </div>
            </Tooltip>
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
};
