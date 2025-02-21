import React, { useCallback } from "react";
import { Input, Switch, Button, Tooltip } from "antd";
import { Edit, HelpCircle, Trash2 } from "lucide-react";
import {
  Component,
  ComponentConfig,
  AgentConfig,
} from "../../../../../types/datamodel";
import {
  isAssistantAgent,
  isUserProxyAgent,
  isWebSurferAgent,
} from "../../../../../types/guards";
import DetailGroup from "../detailgroup";

const { TextArea } = Input;

interface AgentFieldsProps {
  component: Component<AgentConfig>;
  onChange: (updates: Partial<Component<ComponentConfig>>) => void;
  onNavigate?: (componentType: string, id: string, parentField: string) => void;
}

const InputWithTooltip: React.FC<{
  label: string;
  tooltip: string;
  required?: boolean;
  children: React.ReactNode;
}> = ({ label, tooltip, required, children }) => (
  <label className="block">
    <div className="flex items-center gap-2 mb-1">
      <span className="text-sm font-medium text-primary">
        {label} {required && <span className="text-red-500">*</span>}
      </span>
      <Tooltip title={tooltip}>
        <HelpCircle className="w-4 h-4 text-secondary" />
      </Tooltip>
    </div>
    {children}
  </label>
);

export const AgentFields: React.FC<AgentFieldsProps> = ({
  component,
  onChange,
  onNavigate,
}) => {
  if (!component) return null;

  const handleComponentUpdate = useCallback(
    (updates: Partial<Component<ComponentConfig>>) => {
      onChange({
        ...component,
        ...updates,
        config: {
          ...component.config,
          ...(updates.config || {}),
        },
      });
    },
    [component, onChange]
  );

  const handleConfigUpdate = useCallback(
    (field: string, value: unknown) => {
      handleComponentUpdate({
        config: {
          ...component.config,
          [field]: value,
        },
      });
    },
    [component, handleComponentUpdate]
  );

  const handleRemoveTool = useCallback(
    (toolIndex: number) => {
      if (!isAssistantAgent(component)) return;
      const newTools = [...(component.config.tools || [])];
      newTools.splice(toolIndex, 1);
      handleConfigUpdate("tools", newTools);
    },
    [component, handleConfigUpdate]
  );

  const renderNestedComponents = () => {
    if (isAssistantAgent(component)) {
      return (
        <div className="space-y-4">
          {component.config.model_client && (
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-primary">Model Client</h3>
              <div className="bg-secondary p-4 rounded-md">
                <div className="flex items-center justify-between">
                  <span className="text-sm">
                    {component.config.model_client.config.model}
                  </span>
                  {onNavigate && (
                    <Button
                      type="text"
                      icon={<Edit className="w-4 h-4" />}
                      onClick={() => {
                        console.log("model clicked");
                        onNavigate(
                          "model",
                          component.config.model_client?.label || "",
                          "model_client"
                        );
                      }}
                    />
                  )}
                </div>
              </div>
            </div>
          )}

          {component.config.tools && component.config.tools.length > 0 && (
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-primary">Tools</h3>
              <div className="space-y-2">
                {component.config.tools.map((tool, index) => (
                  <div key={tool.label} className="bg-secondary p-4 rounded-md">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">
                        {tool.label || tool.config.name}
                      </span>
                      <div className="flex items-center gap-2">
                        {onNavigate && (
                          <Button
                            type="text"
                            icon={<Edit className="w-4 h-4" />}
                            onClick={() =>
                              onNavigate(
                                "tool",
                                tool.label || tool.config.name || "",
                                "tools"
                              )
                            }
                          />
                        )}
                        <Button
                          type="text"
                          danger
                          icon={<Trash2 className="w-4 h-4" />}
                          onClick={() => handleRemoveTool(index)}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      );
    }

    if (isWebSurferAgent(component)) {
      return (
        <div className="space-y-4">
          {component.config.model_client && (
            <div className="space-y-2">
              <h3 className="text-sm font-medium text-primary">Model Client</h3>
              <div className="bg-secondary p-4 rounded-md">
                <div className="flex items-center justify-between">
                  <span className="text-sm">
                    {component.config.model_client.config.model}
                  </span>
                  {onNavigate && (
                    <Button
                      type="text"
                      icon={<Edit className="w-4 h-4" />}
                      onClick={() =>
                        onNavigate(
                          "model",
                          component.config.model_client?.label || "",
                          "model_client"
                        )
                      }
                    />
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      );
    }

    return (
      <div className="text-sm text-gray-500 text-center">
        No nested components
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <DetailGroup title="Component Details">
        <div className="space-y-4">
          <label className="block">
            <span className="text-sm font-medium text-primary">Name</span>
            <Input
              value={component.label || ""}
              onChange={(e) => handleComponentUpdate({ label: e.target.value })}
              placeholder="Component name"
              className="mt-1"
            />
          </label>

          <label className="block">
            <span className="text-sm font-medium text-primary">
              Description
            </span>
            <TextArea
              value={component.description || ""}
              onChange={(e) =>
                handleComponentUpdate({ description: e.target.value })
              }
              placeholder="Component description"
              rows={4}
              className="mt-1"
            />
          </label>
        </div>
      </DetailGroup>

      <DetailGroup title="Nested Components">
        {renderNestedComponents()}
      </DetailGroup>

      <DetailGroup title="Configuration">
        <div className="space-y-4">
          {isAssistantAgent(component) && (
            <>
              <InputWithTooltip
                label="Name"
                tooltip="Name of the assistant agent"
                required
              >
                <Input
                  value={component.config.name}
                  onChange={(e) => handleConfigUpdate("name", e.target.value)}
                />
              </InputWithTooltip>

              <InputWithTooltip
                label="System Message"
                tooltip="System message for the agent"
              >
                <TextArea
                  rows={4}
                  value={component.config.system_message}
                  onChange={(e) =>
                    handleConfigUpdate("system_message", e.target.value)
                  }
                />
              </InputWithTooltip>

              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-primary">
                  Reflect on Tool Use
                </span>
                <Switch
                  checked={component.config.reflect_on_tool_use}
                  onChange={(checked) =>
                    handleConfigUpdate("reflect_on_tool_use", checked)
                  }
                />
              </div>

              <InputWithTooltip
                label="Tool Call Summary Format"
                tooltip="Format for tool call summaries"
              >
                <Input
                  value={component.config.tool_call_summary_format}
                  onChange={(e) =>
                    handleConfigUpdate(
                      "tool_call_summary_format",
                      e.target.value
                    )
                  }
                />
              </InputWithTooltip>
            </>
          )}

          {isUserProxyAgent(component) && (
            <InputWithTooltip
              label="Name"
              tooltip="Name of the user proxy agent"
              required
            >
              <Input
                value={component.config.name}
                onChange={(e) => handleConfigUpdate("name", e.target.value)}
              />
            </InputWithTooltip>
          )}

          {isWebSurferAgent(component) && (
            // Web surfer specific configuration fields...
            <>
              <InputWithTooltip
                label="Name"
                tooltip="Name of the web surfer agent"
                required
              >
                <Input
                  value={component.config.name}
                  onChange={(e) => handleConfigUpdate("name", e.target.value)}
                />
              </InputWithTooltip>
              {/* Add other web surfer fields here */}
            </>
          )}
        </div>
      </DetailGroup>
    </div>
  );
};

export default React.memo(AgentFields);
