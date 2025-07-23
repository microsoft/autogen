import React, { useState } from "react";
import { Button } from "antd";
import {
  ChevronDown,
  ChevronRight,
  Database,
  Eye,
  EyeOff,
  History,
} from "lucide-react";
import { WorkflowExecution } from "./types";

interface StateInspectorProps {
  execution?: WorkflowExecution;
  isCompact?: boolean;
  onToggleCompact?: () => void;
}

interface StateValue {
  key: string;
  value: any;
  isStepOutput: boolean;
}

export const StateInspector: React.FC<StateInspectorProps> = ({
  execution,
  isCompact = false,
  onToggleCompact,
}) => {
  const [expandedKeys, setExpandedKeys] = useState<Set<string>>(new Set());
  const [showStepOutputs, setShowStepOutputs] = useState(true);
  const [showCustomVars, setShowCustomVars] = useState(true);

  const toggleExpanded = (key: string) => {
    const newExpanded = new Set(expandedKeys);
    if (newExpanded.has(key)) {
      newExpanded.delete(key);
    } else {
      newExpanded.add(key);
    }
    setExpandedKeys(newExpanded);
  };

  const formatValue = (value: any): string => {
    if (value === null) return "null";
    if (value === undefined) return "undefined";
    if (typeof value === "string") return `"${value}\"`;
    if (typeof value === "object") {
      try {
        return JSON.stringify(value, null, 2);
      } catch {
        return String(value);
      }
    }
    return String(value);
  };

  const getStateVariables = (): StateValue[] => {
    if (!execution?.state) return [];

    return Object.entries(execution.state).map(([key, value]) => ({
      key,
      value,
      isStepOutput: key.endsWith("_output"),
    }));
  };

  const stateVariables = getStateVariables();
  const stepOutputs = stateVariables.filter((v) => v.isStepOutput);
  const customVars = stateVariables.filter((v) => !v.isStepOutput);

  const renderValue = (value: any, key: string, isRoot = false) => {
    const isExpanded = expandedKeys.has(key);
    const isObject = typeof value === "object" && value !== null;
    const displayValue = isObject
      ? isExpanded
        ? formatValue(value)
        : `{...} (${Object.keys(value).length} keys)`
      : formatValue(value);

    return (
      <div className={`${isRoot ? "mb-2" : "ml-4"}`}>
        <div className="flex items-center gap-2">
          {isObject && (
            <button
              onClick={() => toggleExpanded(key)}
              className="text-secondary hover:text-primary"
            >
              {isExpanded ? (
                <ChevronDown size={14} />
              ) : (
                <ChevronRight size={14} />
              )}
            </button>
          )}
          <span className="font-mono text-xs text-accent font-medium">
            {key}:
          </span>
          <span className="font-mono text-xs text-secondary break-all">
            {isExpanded && isObject ? (
              <pre className="whitespace-pre-wrap text-xs mt-1 p-2 bg-tertiary rounded">
                {displayValue}
              </pre>
            ) : (
              displayValue
            )}
          </span>
        </div>
      </div>
    );
  };

  if (isCompact) {
    return (
      <div className="w-12 border-l border-secondary bg-tertiary flex flex-col items-center py-2">
        <Button
          type="text"
          icon={<Database size={16} />}
          onClick={onToggleCompact}
          className="!p-1 text-secondary hover:text-accent"
          title="Expand State Inspector"
        />
        {execution?.state && Object.keys(execution.state).length > 0 && (
          <div className="mt-2 w-2 h-2 bg-green-500 rounded-full" />
        )}
      </div>
    );
  }

  return (
    <div className="w-80 border-l border-secondary bg-tertiary h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-secondary">
        <div className="flex items-center gap-2">
          <Database size={16} className="text-accent" />
          <span className="text-sm font-medium text-primary">
            Workflow State
          </span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            type="text"
            size="small"
            icon={<History size={14} />}
            className="text-secondary hover:text-accent"
            title="State History (Coming Soon)"
            disabled
          />
          <Button
            type="text"
            size="small"
            icon={<Database size={14} />}
            onClick={onToggleCompact}
            className="text-secondary hover:text-accent"
            title="Collapse State Inspector"
          />
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-3">
        {!execution?.state || Object.keys(execution.state).length === 0 ? (
          <div className="text-center text-secondary py-8">
            <Database size={24} className="mx-auto mb-2 opacity-50" />
            <p className="text-sm">No state data available</p>
            <p className="text-xs mt-1">
              State variables will appear here during workflow execution
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Custom State Variables */}
            {customVars.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <button
                    onClick={() => setShowCustomVars(!showCustomVars)}
                    className="text-primary hover:text-accent"
                  >
                    {showCustomVars ? (
                      <EyeOff size={14} />
                    ) : (
                      <Eye size={14} />
                    )}
                  </button>
                  <h3 className="text-sm font-medium text-primary">
                    State Variables ({customVars.length})
                  </h3>
                </div>
                {showCustomVars &&
                  customVars.map((variable) =>
                    renderValue(variable.value, variable.key, true)
                  )}
              </div>
            )}

            {/* Step Outputs */}
            {stepOutputs.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <button
                    onClick={() => setShowStepOutputs(!showStepOutputs)}
                    className="text-primary hover:text-accent"
                  >
                    {showStepOutputs ? (
                      <EyeOff size={14} />
                    ) : (
                      <Eye size={14} />
                    )}
                  </button>
                  <h3 className="text-sm font-medium text-primary">
                    Step Outputs ({stepOutputs.length})
                  </h3>
                </div>
                {showStepOutputs &&
                  stepOutputs.map((variable) =>
                    renderValue(variable.value, variable.key, true)
                  )}
              </div>
            )}

            {/* Debug Info */}
            <div className="pt-2 border-t border-secondary">
              <p className="text-xs text-secondary">
                Total variables: {stateVariables.length}
              </p>
              <p className="text-xs text-secondary">
                Execution ID: {execution?.id || "N/A"}
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};