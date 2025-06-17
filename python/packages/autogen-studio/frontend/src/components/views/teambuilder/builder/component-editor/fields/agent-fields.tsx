import React, { useCallback } from "react";
import { Input, Switch, Button, Tooltip } from "antd";
import { Edit, HelpCircle, Trash2, PlusCircle } from "lucide-react";
import {
  Component,
  ComponentConfig,
  AgentConfig,
  FunctionToolConfig,
  StaticWorkbenchConfig,
  WorkbenchConfig,
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
  workingCopy?: Component<ComponentConfig> | null;
  setWorkingCopy?: (component: Component<ComponentConfig> | null) => void;
  editPath?: any[];
  updateComponentAtPath?: any;
  getCurrentComponent?: any;
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
  workingCopy,
  setWorkingCopy,
  editPath,
  updateComponentAtPath,
  getCurrentComponent,
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

      // Get workbench or create one if it doesn't exist
      let workbench = component.config.workbench;
      if (
        !workbench ||
        workbench.provider !== "autogen_core.tools.StaticWorkbench"
      ) {
        return; // Can't remove tools if no StaticWorkbench exists
      }

      const staticConfig = workbench.config as StaticWorkbenchConfig;
      const newTools = [...(staticConfig.tools || [])];
      newTools.splice(toolIndex, 1);

      // Update workbench config
      const updatedWorkbench = {
        ...workbench,
        config: {
          ...staticConfig,
          tools: newTools,
        },
      };

      handleConfigUpdate("workbench", updatedWorkbench);
    },
    [component, handleConfigUpdate]
  );

  const handleAddTool = useCallback(() => {
    if (!isAssistantAgent(component)) return;

    const blankTool: Component<FunctionToolConfig> = {
      provider: "autogen_core.tools.FunctionTool",
      component_type: "tool",
      version: 1,
      component_version: 1,
      description: "Create custom tools by wrapping standard Python functions.",
      label: "New Tool",
      config: {
        source_code: "def new_function():\n    pass",
        name: "new_function",
        description: "Description of the new function",
        global_imports: [],
        has_cancellation_support: false,
      },
    };

    // Get or create workbench
    let workbench = component.config.workbench;
    if (!workbench) {
      // Create a new StaticWorkbench
      workbench = {
        provider: "autogen_core.tools.StaticWorkbench",
        component_type: "workbench",
        config: {
          tools: [],
        },
        label: "Static Workbench",
      } as Component<StaticWorkbenchConfig>;
    }

    // Ensure it's a StaticWorkbench (since only StaticWorkbench supports tools)
    if (workbench.provider !== "autogen_core.tools.StaticWorkbench") {
      return; // Can't add tools to MCP workbench from UI
    }

    const staticConfig = workbench.config as StaticWorkbenchConfig;
    const currentTools = staticConfig.tools || [];
    const updatedTools = [...currentTools, blankTool];

    // Update workbench config
    const updatedWorkbench = {
      ...workbench,
      config: {
        ...staticConfig,
        tools: updatedTools,
      },
    };

    handleConfigUpdate("workbench", updatedWorkbench);

    // If working copy functionality is available, update that too
    if (
      workingCopy &&
      setWorkingCopy &&
      updateComponentAtPath &&
      getCurrentComponent &&
      editPath
    ) {
      const updatedCopy = updateComponentAtPath(workingCopy, editPath, {
        config: {
          ...getCurrentComponent(workingCopy)?.config,
          workbench: updatedWorkbench,
        },
      });
      setWorkingCopy(updatedCopy);
    }
  }, [
    component,
    handleConfigUpdate,
    workingCopy,
    setWorkingCopy,
    updateComponentAtPath,
    getCurrentComponent,
    editPath,
  ]);

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

              {/* Model Client Section */}

              <div className="space-y-2">
                <span className="text-sm font-medium text-primary">
                  Model Client
                </span>
                {component.config.model_client ? (
                  <div className="bg-secondary p-1 px-2 rounded-md">
                    <div className="flex items-center justify-between">
                      {" "}
                      <span className="text-sm">
                        {component.config.model_client.config.model}
                      </span>
                      <div className="flex items-center justify-between">
                        {component.config.model_client && onNavigate && (
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
                          >
                            Configure Model
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-secondary text-center bg-secondary/50 p-4 rounded-md">
                    No model configured
                  </div>
                )}
              </div>

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

              {/* Tools Section */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-primary">
                    Tools
                  </span>
                  <Button
                    type="dashed"
                    size="small"
                    onClick={handleAddTool}
                    icon={<PlusCircle className="w-4 h-4" />}
                  >
                    Add Tool
                  </Button>
                </div>
                <div className="space-y-2">
                  {(() => {
                    // Get tools from workbench
                    const workbench = component.config.workbench;
                    const tools =
                      workbench?.provider ===
                      "autogen_core.tools.StaticWorkbench"
                        ? (workbench.config as StaticWorkbenchConfig).tools ||
                          []
                        : [];

                    return tools.map((tool, index) => (
                      <div
                        key={(tool.label || "") + index}
                        className="bg-secondary p-1 px-2 rounded-md"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-sm">
                            {tool.config.name || tool.label || ""}
                          </span>
                          <div className="flex items-center gap-2">
                            {onNavigate && (
                              <Button
                                type="text"
                                icon={<Edit className="w-4 h-4" />}
                                onClick={() =>
                                  onNavigate(
                                    "tool",
                                    tool.config.name || tool.label || "",
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
                    ));
                  })()}
                  {(() => {
                    const workbench = component.config.workbench;
                    const tools =
                      workbench?.provider ===
                      "autogen_core.tools.StaticWorkbench"
                        ? (workbench.config as StaticWorkbenchConfig).tools ||
                          []
                        : [];

                    return (
                      tools.length === 0 && (
                        <div className="text-sm text-secondary text-center bg-secondary/50 p-4 rounded-md">
                          No tools configured
                        </div>
                      )
                    );
                  })()}
                </div>
              </div>

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

              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-primary">
                  Stream Model Client
                </span>
                <Switch
                  checked={component.config.model_client_stream}
                  onChange={(checked) =>
                    handleConfigUpdate("model_client_stream", checked)
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
              <InputWithTooltip
                label="Start Page"
                tooltip="URL to start browsing from"
              >
                <Input
                  value={component.config.start_page || ""}
                  onChange={(e) =>
                    handleConfigUpdate("start_page", e.target.value)
                  }
                />
              </InputWithTooltip>
              <InputWithTooltip
                label="Downloads Folder"
                tooltip="Folder path to save downloads"
              >
                <Input
                  value={component.config.downloads_folder || ""}
                  onChange={(e) =>
                    handleConfigUpdate("downloads_folder", e.target.value)
                  }
                />
              </InputWithTooltip>
              <InputWithTooltip
                label="Debug Directory"
                tooltip="Directory for debugging logs"
              >
                <Input
                  value={component.config.debug_dir || ""}
                  onChange={(e) =>
                    handleConfigUpdate("debug_dir", e.target.value)
                  }
                />
              </InputWithTooltip>

              {/* Added Model Client Section for WebSurferAgent */}
              <div className="space-y-2">
                <span className="text-sm font-medium text-primary">
                  Model Client
                </span>
                {component.config.model_client ? (
                  <div className="bg-secondary p-1 px-2 rounded-md">
                    <div className="flex items-center justify-between">
                      <span className="text-sm">
                        {component.config.model_client.config.model}
                      </span>
                      <div className="flex items-center justify-between">
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
                          >
                            Configure Model
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-secondary text-center bg-secondary/50 p-4 rounded-md">
                    No model configured
                  </div>
                )}
              </div>

              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-primary">
                  Headless
                </span>
                <Switch
                  checked={component.config.headless || false}
                  onChange={(checked) =>
                    handleConfigUpdate("headless", checked)
                  }
                />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-primary">
                  Animate Actions
                </span>
                <Switch
                  checked={component.config.animate_actions || false}
                  onChange={(checked) =>
                    handleConfigUpdate("animate_actions", checked)
                  }
                />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-primary">
                  Save Screenshots
                </span>
                <Switch
                  checked={component.config.to_save_screenshots || false}
                  onChange={(checked) =>
                    handleConfigUpdate("to_save_screenshots", checked)
                  }
                />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-primary">
                  Use OCR
                </span>
                <Switch
                  checked={component.config.use_ocr || false}
                  onChange={(checked) => handleConfigUpdate("use_ocr", checked)}
                />
              </div>
              <InputWithTooltip
                label="Browser Channel"
                tooltip="Channel for the browser (e.g. beta, stable)"
              >
                <Input
                  value={component.config.browser_channel || ""}
                  onChange={(e) =>
                    handleConfigUpdate("browser_channel", e.target.value)
                  }
                />
              </InputWithTooltip>
              <InputWithTooltip
                label="Browser Data Directory"
                tooltip="Directory for browser profile data"
              >
                <Input
                  value={component.config.browser_data_dir || ""}
                  onChange={(e) =>
                    handleConfigUpdate("browser_data_dir", e.target.value)
                  }
                />
              </InputWithTooltip>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-primary">
                  Resize Viewport
                </span>
                <Switch
                  checked={component.config.to_resize_viewport || false}
                  onChange={(checked) =>
                    handleConfigUpdate("to_resize_viewport", checked)
                  }
                />
              </div>
            </>
          )}
        </div>
      </DetailGroup>
    </div>
  );
};

export default React.memo(AgentFields);
