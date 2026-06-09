import React from "react";
import { Alert } from "antd";
import { AlertTriangle } from "lucide-react";
import {
  Component,
  ComponentConfig,
} from "../../../../../types/datamodel";
import { isFunctionTool } from "../../../../../types/guards";

interface ToolFieldsProps {
  component: Component<ComponentConfig>;
  onChange: (updates: Partial<Component<ComponentConfig>>) => void;
}

/**
 * ToolFields component - displays a deprecation warning for FunctionTool.
 *
 * FunctionTool has been deprecated due to security concerns:
 * - FunctionTool uses exec() to execute user-provided Python code
 * - This creates a Remote Code Execution (RCE) vulnerability
 * - The /api/validate/ endpoint could be exploited via drive-by attacks
 *
 * Users should migrate to MCP Workbenches for custom tool functionality.
 * MCP provides better security through process isolation.
 */
export const ToolFields: React.FC<ToolFieldsProps> = ({
  component,
  onChange,
}) => {
  if (!isFunctionTool(component)) return null;

  return (
    <div className="space-y-4 p-4">
      <Alert
        message="FunctionTool Deprecated"
        description={
          <div className="space-y-2">
            <p>
              <strong>FunctionTool has been deprecated due to security concerns.</strong>
            </p>
            <p>
              FunctionTool executes arbitrary Python code, which creates security
              vulnerabilities. This component type is no longer supported for new
              configurations.
            </p>
            <p>
              <strong>Recommended alternative:</strong> Use an{" "}
              <span className="font-mono bg-gray-100 px-1 rounded">MCP Workbench</span>{" "}
              instead. MCP (Model Context Protocol) servers provide the same tool
              functionality with better security through process isolation.
            </p>
            <p className="text-sm text-gray-600 mt-2">
              Existing FunctionTool configurations in the gallery will continue to
              work, but creating or editing FunctionTool source code is no longer
              available in the UI.
            </p>
          </div>
        }
        type="warning"
        showIcon
        icon={<AlertTriangle className="w-5 h-5" />}
      />

      {/* Show read-only info about the existing tool */}
      {component.config.name && (
        <div className="bg-gray-50 rounded p-3 space-y-2">
          <div>
            <span className="text-sm font-medium text-gray-500">Tool Name:</span>
            <span className="ml-2 text-sm">{component.config.name}</span>
          </div>
          {component.config.description && (
            <div>
              <span className="text-sm font-medium text-gray-500">Description:</span>
              <span className="ml-2 text-sm">{component.config.description}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default React.memo(ToolFields);
