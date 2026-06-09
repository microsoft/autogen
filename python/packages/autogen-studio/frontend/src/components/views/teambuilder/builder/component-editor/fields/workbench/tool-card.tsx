import React from "react";
import { Button, Typography } from "antd";
import {
  Wrench,
  ChevronUp,
  Info,
  Hash,
  Shield,
  AlertTriangle,
  RotateCcw,
  Globe,
} from "lucide-react";
import { Tool } from "../../../../../mcp/api";

const { Text } = Typography;

interface ToolCardProps {
  tool: Tool;
  isSelected: boolean;
  isExpanded: boolean;
  onSelect: (tool: Tool) => void;
  onToggleExpansion: (toolName: string) => void;
}

export const ToolCard: React.FC<ToolCardProps> = ({
  tool,
  isSelected,
  isExpanded,
  onSelect,
  onToggleExpansion,
}) => {
  // Helper function to get tool display name following MCP precedence rules
  const getToolDisplayName = (tool: Tool): string => {
    return tool.annotations?.title || tool.name;
  };

  // Helper function to get annotation badges
  const getAnnotationBadges = (tool: Tool) => {
    const badges = [];
    const annotations = tool.annotations;

    if (annotations?.readOnlyHint) {
      badges.push({
        key: "readonly",
        icon: <Shield size={12} />,
        label: "Read-only",
        color: "text-green-600 bg-green-50 border-green-200",
      });
    }
    if (annotations?.destructiveHint) {
      badges.push({
        key: "destructive",
        icon: <AlertTriangle size={12} />,
        label: "Destructive",
        color: "text-red-600 bg-red-50 border-red-200",
      });
    }
    if (annotations?.idempotentHint) {
      badges.push({
        key: "idempotent",
        icon: <RotateCcw size={12} />,
        label: "Safe to retry",
        color: "text-blue-600 bg-blue-50 border-blue-200",
      });
    }
    if (annotations?.openWorldHint) {
      badges.push({
        key: "openworld",
        icon: <Globe size={12} />,
        label: "Open World",
        color: "text-purple-600 bg-purple-50 border-purple-200",
      });
    }

    return badges;
  };

  // Get parameter count for a tool
  const getParameterCount = (tool: Tool): number => {
    return Object.keys(tool.inputSchema?.properties || {}).length;
  };

  const displayName = getToolDisplayName(tool);
  const badges = getAnnotationBadges(tool);
  const paramCount = getParameterCount(tool);

  // Better description truncation for compact cards
  const maxDescLength = isExpanded ? 150 : 35;
  const truncatedDescription =
    tool.description && tool.description.length > maxDescLength
      ? `${tool.description.substring(0, maxDescLength)}...`
      : tool.description || "No description available";

  return (
    <div className="min-w-60 max-w-70 flex-shrink-0">
      <div
        onClick={() => onSelect(tool)}
        className={`
          cursor-pointer rounded-lg border-2 transition-all duration-200 ease-in-out
          p-2.5 flex flex-col bg-white hover:shadow-md
          ${isExpanded ? "h-auto" : "h-[90px]"}
          ${
            isSelected
              ? "border-blue-500 shadow-lg shadow-blue-100"
              : "border-gray-300 shadow-sm"
          }
        `}
      >
        {/* Card Header */}
        <div className="flex items-start justify-between mb-1.5 min-h-[18px]">
          <div className="flex items-center gap-1.5 flex-1 overflow-hidden">
            <Wrench
              size={12}
              className={`flex-shrink-0 ${
                isSelected ? "text-blue-500" : "text-gray-500"
              }`}
            />
            <Text
              strong
              className={`
                text-xs leading-[18px] truncate
                ${isSelected ? "text-blue-500" : "text-gray-800"}
              `}
              title={displayName}
            >
              {displayName}
            </Text>
          </div>
          <Button
            type="text"
            size="small"
            icon={isExpanded ? <ChevronUp size={10} /> : <Info size={10} />}
            onClick={(e) => {
              e.stopPropagation();
              onToggleExpansion(tool.name);
            }}
            className="p-0.5 min-w-0 h-[18px] w-[18px] flex-shrink-0"
          />
        </div>

        {/* Description */}
        <div
          className={`
            flex-1 mb-1.5 overflow-hidden flex flex-col
            ${isExpanded ? "h-auto" : "h-[26px]"}
          `}
        >
          <div
            className={`
              text-[10px] leading-[13px] text-gray-500 overflow-hidden break-words
              ${isExpanded ? "" : "line-clamp-2"}
            `}
            style={{
              display: isExpanded ? "block" : "-webkit-box",
              WebkitLineClamp: isExpanded ? "none" : 2,
              WebkitBoxOrient: "vertical",
            }}
          >
            {truncatedDescription}
          </div>
        </div>

        {/* Expanded Details */}
        {isExpanded && (
          <div className="mb-1.5 border-t border-gray-100 pt-1.5">
            <div className="mb-0.5">
              <Text strong className="text-[9px]">
                Parameters:
              </Text>
            </div>
            <div className="max-h-[60px] overflow-y-auto text-[9px]">
              {Object.keys(tool.inputSchema?.properties || {}).length === 0 ? (
                <Text className="text-gray-400 text-[9px]">No parameters</Text>
              ) : (
                Object.entries(tool.inputSchema?.properties || {}).map(
                  ([key, schema]: [string, any]) => (
                    <div
                      key={key}
                      className="mb-0.5 flex items-center gap-0.5 flex-wrap"
                    >
                      <code className="text-[8px] bg-gray-100 px-0.5 py-0.5 rounded max-w-20 overflow-hidden text-ellipsis">
                        {key}
                      </code>
                      <Text className="text-gray-400 text-[8px]">
                        {schema.type || "any"}
                      </Text>
                      {tool.inputSchema?.required?.includes(key) && (
                        <div className="text-[7px] text-red-600 bg-red-50 border border-red-200 rounded px-0.5 leading-[10px]">
                          req
                        </div>
                      )}
                    </div>
                  )
                )
              )}
            </div>
          </div>
        )}

        {/* Footer with badges and param count */}
        <div className="flex items-center justify-between mt-auto min-h-[14px]">
          <div className="flex gap-0.5 flex-wrap items-center">
            {badges.map((badge) => (
              <div
                key={badge.key}
                className={`
                  inline-flex items-center px-0.5 py-0.5 rounded border
                  ${badge.color}
                `}
                title={badge.label}
              >
                <span className="text-[10px]">{badge.icon}</span>
              </div>
            ))}
          </div>
          <div className="flex items-center gap-0.5 flex-shrink-0">
            <Hash size={8} className="text-gray-500" />
            <Text className="text-[8px] text-gray-500">{paramCount}</Text>
          </div>
        </div>
      </div>
    </div>
  );
};
