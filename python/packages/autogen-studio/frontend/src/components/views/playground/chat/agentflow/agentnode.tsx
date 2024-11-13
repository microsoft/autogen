import React, { useCallback } from "react";
import { Handle, Position } from "@xyflow/react";
import {
  CheckCircle,
  AlertTriangle,
  StopCircle,
  UserCircle,
  Bot,
  Flag,
} from "lucide-react";
import { ThreadStatus } from "../../../../types/datamodel";

export type NodeType = "agent" | "user" | "end";

export interface AgentNodeData {
  type: NodeType;
  label: string;
  agentType?: string;
  description?: string;
  isActive?: boolean;
  status?: ThreadStatus | null;
  reason?: string | null;
}

interface AgentNodeProps {
  data: AgentNodeData;
  isConnectable: boolean;
}

function AgentNode({ data, isConnectable }: AgentNodeProps) {
  const handleClick = useCallback(() => {
    if (data.type !== "end") {
      console.log(`${data.type} ${data.label} clicked`);
    }
  }, [data.type, data.label]);

  const getHeaderIcon = () => {
    switch (data.type) {
      case "user":
        return <UserCircle className="text-primary" size={20} />;
      case "agent":
        return <Bot className="text-primary" size={20} />;
      case "end":
        return <Flag className="text-primary" size={20} />;
    }
  };

  const getStatusIcon = () => {
    if (data.type !== "end" || !data.status) return null;

    switch (data.status) {
      case "complete":
        return <CheckCircle className="text-accent" size={24} />;
      case "error":
        return <AlertTriangle className="text-red-500" size={24} />;
      case "cancelled":
        return <StopCircle className="text-red-500" size={24} />;
      default:
        return null;
    }
  };

  const getNodeStyles = () => {
    const activeStyles = data.isActive ? "ring-2 ring-accent/50 " : "  ";

    if (data.type === "end") {
      return {
        wrapper: `relative min-w-[120px] shadow rounded-lg overflow-hidden  ${activeStyles}`,
        border:
          data.status === "complete"
            ? "var(--accent)"
            : data.status === "error"
            ? "rgb(239 68 68)"
            : "var(--secondary)",
      };
    }

    return {
      wrapper: `min-w-[150px] rounded-lg shadow overflow-hidden ${activeStyles}`,
      border: undefined,
    };
  };

  const styles = getNodeStyles();

  return (
    <div
      className={styles.wrapper}
      onClick={handleClick}
      style={styles.border ? { borderColor: styles.border } : undefined}
    >
      {/* Input handle - always show for all nodes */}
      <Handle
        type="target"
        position={Position.Top}
        style={{ background: "#555" }}
        isConnectable={isConnectable}
        id="target"
      />

      {/* Header Section */}
      <div className="flex items-center gap-2 px-3 py-2 bg-secondary border-b border-border">
        {getHeaderIcon()}
        <span className="text-sm font-medium text-primary truncate">
          {data.label}
        </span>
      </div>

      {/* Content Section */}
      <div className="bg-tertiary px-3 py-2">
        {data.type === "end" ? (
          <>
            <div className="flex items-center justify-center gap-2">
              {getStatusIcon()}
              <span className="text-primary text-sm font-medium">
                {data.status &&
                  data.status.charAt(0).toUpperCase() + data.status.slice(1)}
              </span>
            </div>
            {data.reason && (
              <div className="mt-1 text-xs text-secondary max-w-[200px] text-center">
                {data.reason.length > 100
                  ? `${data.reason.substring(0, 97)}...`
                  : data.reason}
              </div>
            )}
          </>
        ) : (
          <>
            {data.agentType && (
              <div className="text-sm text-secondary">{data.agentType}</div>
            )}
            {data.description && (
              <div className="text-xs text-secondary mt-1 truncate max-w-[200px]">
                {data.description}
              </div>
            )}
          </>
        )}
      </div>

      {/* Output handle - only for non-end nodes */}
      {data.type !== "end" && (
        <Handle
          type="source"
          position={Position.Bottom}
          id="source"
          style={{ background: "#555" }}
          isConnectable={isConnectable}
        />
      )}
    </div>
  );
}

export default AgentNode;
