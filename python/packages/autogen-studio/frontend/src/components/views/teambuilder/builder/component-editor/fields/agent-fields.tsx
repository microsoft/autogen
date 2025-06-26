import React, { useCallback, useState } from "react";
import {
  Input,
  Switch,
  Button,
  Tooltip,
  Collapse,
  InputNumber,
  Dropdown,
} from "antd";
import {
  Edit,
  HelpCircle,
  Trash2,
  PlusCircle,
  ChevronDown,
  Wrench,
  User,
  Settings,
  Code,
} from "lucide-react";
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
  isStaticWorkbench,
  isMcpWorkbench,
} from "../../../../../types/guards";

const { TextArea } = Input;

// Helper function to normalize workbench format (handle both single object and array)
const normalizeWorkbenches = (
  workbench:
    | Component<WorkbenchConfig>[]
    | Component<WorkbenchConfig>
    | undefined
): Component<WorkbenchConfig>[] => {
  if (!workbench) return [];
  return Array.isArray(workbench) ? workbench : [workbench];
};

interface AgentFieldsProps {
  component: Component<AgentConfig>;
  onChange: (updates: Partial<Component<ComponentConfig>>) => void;
  onNavigate?: (
    componentType: string,
    id: string,
    parentField: string,
    index?: number
  ) => void;
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

    // Get or create workbenches array
    let workbenches = normalizeWorkbenches(component.config.workbench);

    // Find existing StaticWorkbench or create one
    let workbenchIndex = workbenches.findIndex((wb) => isStaticWorkbench(wb));

    let workbench: Component<StaticWorkbenchConfig>;
    if (workbenchIndex === -1) {
      // Create a new StaticWorkbench
      workbench = {
        provider: "autogen_core.tools.StaticWorkbench",
        component_type: "workbench",
        config: {
          tools: [],
        },
        label: "Static Workbench",
      } as Component<StaticWorkbenchConfig>;
      workbenches = [...workbenches, workbench];
      workbenchIndex = workbenches.length - 1;
    } else {
      workbench = workbenches[
        workbenchIndex
      ] as Component<StaticWorkbenchConfig>;
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

    // Update the workbenches array
    const updatedWorkbenches = [...workbenches];
    updatedWorkbenches[workbenchIndex] = updatedWorkbench;

    handleConfigUpdate("workbench", updatedWorkbenches);

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
          workbench: updatedWorkbenches,
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

  // Helper functions to add different types of workbenches
  const addStaticWorkbench = useCallback(() => {
    if (!isAssistantAgent(component)) return;

    const existingWorkbenches = normalizeWorkbenches(
      component.config.workbench
    );
    const staticWorkbenchCount = existingWorkbenches.filter((wb) =>
      isStaticWorkbench(wb)
    ).length;
    const workbenchId = `static-workbench-${Date.now()}`; // Unique ID

    const newWorkbench: Component<WorkbenchConfig> = {
      provider: "autogen_core.tools.StaticWorkbench",
      component_type: "workbench",
      version: 1,
      component_version: 1,
      config: { tools: [] },
      label:
        staticWorkbenchCount > 0
          ? `Static Workbench ${staticWorkbenchCount + 1}`
          : "Static Workbench",
      description: "A static workbench for managing custom tools",
    };
    const normalizedWorkbenches = normalizeWorkbenches(
      component.config.workbench
    );
    handleConfigUpdate("workbench", [...normalizedWorkbenches, newWorkbench]);
  }, [component, handleConfigUpdate]);

  const addStdioMcpWorkbench = useCallback(() => {
    if (!isAssistantAgent(component)) return;

    const existingWorkbenches = normalizeWorkbenches(
      component.config.workbench
    );
    const mcpWorkbenchCount = existingWorkbenches.filter((wb) =>
      isMcpWorkbench(wb)
    ).length;

    const newMcpWorkbench: Component<WorkbenchConfig> = {
      provider: "autogen_ext.tools.mcp.McpWorkbench",
      component_type: "workbench",
      version: 1,
      component_version: 1,
      config: {
        server_params: {
          type: "StdioServerParams",
          command: "server-command",
          args: [],
          env: {},
        },
      },
      label:
        mcpWorkbenchCount > 0
          ? `Stdio MCP Workbench ${mcpWorkbenchCount + 1}`
          : "Stdio MCP Workbench",
      description: "An MCP workbench that connects via stdio to local servers",
    };
    const normalizedWorkbenches = normalizeWorkbenches(
      component.config.workbench
    );
    const updatedWorkbenches = [...normalizedWorkbenches, newMcpWorkbench];
    handleConfigUpdate("workbench", updatedWorkbenches);

    // Navigate to edit the newly created workbench if navigation is available
    if (onNavigate) {
      const workbenchIndex = updatedWorkbenches.length - 1; // New workbench is at the end
      onNavigate(
        "workbench",
        newMcpWorkbench.label || "Stdio MCP Workbench",
        "workbench",
        workbenchIndex
      );
    }
  }, [component, handleConfigUpdate, onNavigate]);

  const addStreamableMcpWorkbench = useCallback(() => {
    if (!isAssistantAgent(component)) return;

    const existingWorkbenches = normalizeWorkbenches(
      component.config.workbench
    );
    const mcpWorkbenchCount = existingWorkbenches.filter((wb) =>
      isMcpWorkbench(wb)
    ).length;

    const newMcpWorkbench: Component<WorkbenchConfig> = {
      provider: "autogen_ext.tools.mcp.McpWorkbench",
      component_type: "workbench",
      version: 1,
      component_version: 1,
      config: {
        server_params: {
          type: "StreamableHttpServerParams",
          url: "https://example.com/mcp",
          headers: {},
          timeout: 30,
          sse_read_timeout: 300,
          terminate_on_close: true,
        },
      },
      label:
        mcpWorkbenchCount > 0
          ? `Streamable MCP Workbench ${mcpWorkbenchCount + 1}`
          : "Streamable MCP Workbench",
      description:
        "An MCP workbench that connects via HTTP streaming to remote servers",
    };
    const normalizedWorkbenches = normalizeWorkbenches(
      component.config.workbench
    );
    const updatedWorkbenches = [...normalizedWorkbenches, newMcpWorkbench];
    handleConfigUpdate("workbench", updatedWorkbenches);

    // Navigate to edit the newly created workbench if navigation is available
    if (onNavigate) {
      const workbenchIndex = updatedWorkbenches.length - 1; // New workbench is at the end
      onNavigate(
        "workbench",
        newMcpWorkbench.label || "Streamable MCP Workbench",
        "workbench",
        workbenchIndex
      );
    }
  }, [component, handleConfigUpdate, onNavigate]);

  const addSseMcpWorkbench = useCallback(() => {
    if (!isAssistantAgent(component)) return;

    const existingWorkbenches = normalizeWorkbenches(
      component.config.workbench
    );
    const mcpWorkbenchCount = existingWorkbenches.filter((wb) =>
      isMcpWorkbench(wb)
    ).length;

    const newMcpWorkbench: Component<WorkbenchConfig> = {
      provider: "autogen_ext.tools.mcp.McpWorkbench",
      component_type: "workbench",
      version: 1,
      component_version: 1,
      config: {
        server_params: {
          type: "SseServerParams",
          url: "https://example.com/mcp/sse",
          headers: {},
          timeout: 30,
          sse_read_timeout: 300,
        },
      },
      label:
        mcpWorkbenchCount > 0
          ? `SSE MCP Workbench ${mcpWorkbenchCount + 1}`
          : "SSE MCP Workbench",
      description:
        "An MCP workbench that connects via Server-Sent Events to remote servers",
    };
    const normalizedWorkbenches = normalizeWorkbenches(
      component.config.workbench
    );
    const updatedWorkbenches = [...normalizedWorkbenches, newMcpWorkbench];
    handleConfigUpdate("workbench", updatedWorkbenches);

    // Navigate to edit the newly created workbench if navigation is available
    if (onNavigate) {
      const workbenchIndex = updatedWorkbenches.length - 1; // New workbench is at the end
      onNavigate(
        "workbench",
        newMcpWorkbench.label || "SSE MCP Workbench",
        "workbench",
        workbenchIndex
      );
    }
  }, [component, handleConfigUpdate, onNavigate]);

  const label = component.config.name || component.label || "Unnamed Agent";
  const displayName =
    label.length > 20 ? `${label.substring(0, 30)}...` : label;
  return (
    <Collapse
      defaultActiveKey={["configuration"]}
      className="border-0"
      expandIconPosition="end"
      items={[
        {
          key: "details",
          label: (
            <div className="flex items-center gap-2">
              <User className="w-4 h-4 text-blue-500" />
              <span className="font-medium">
                Agent Details
                <span className="text-xs font-normal text-secondary ml-2">
                  {displayName}
                </span>
              </span>
            </div>
          ),
          children: (
            <>
              {/* Component Details Section */}
              <div className="border border-secondary rounded-lg p-3">
                <div className="border-b border-secondary pb-2 mb-4">
                  <h3 className="text-sm font-medium text-primary">
                    Component Details
                  </h3>
                </div>
                <div className="space-y-4">
                  <label className="block">
                    <span className="text-sm font-medium text-primary">
                      Name
                    </span>
                    <Input
                      value={component.label || ""}
                      onChange={(e) =>
                        handleComponentUpdate({ label: e.target.value })
                      }
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

                  <div className="grid grid-cols-2 gap-4">
                    <label className="block">
                      <span className="text-sm font-medium text-primary">
                        Version
                      </span>
                      <InputNumber
                        min={1}
                        precision={0}
                        className="w-full mt-1"
                        placeholder="e.g., 1"
                        value={component.version || undefined}
                        onChange={(value) =>
                          handleComponentUpdate({ version: value || undefined })
                        }
                      />
                    </label>
                    <label className="block">
                      <span className="text-sm font-medium text-primary">
                        Component Version
                      </span>
                      <InputNumber
                        min={1}
                        precision={0}
                        className="w-full mt-1"
                        placeholder="e.g., 1"
                        value={component.component_version || undefined}
                        onChange={(value) =>
                          handleComponentUpdate({
                            component_version: value || undefined,
                          })
                        }
                      />
                    </label>
                  </div>
                </div>
              </div>
            </>
          ),
        },
        {
          key: "configuration",
          label: (
            <div className="flex items-center gap-2">
              <Settings className="w-4 h-4 text-green-500" />
              <span className="font-medium">Agent Configuration</span>
            </div>
          ),
          children: (
            <>
              {/* Configuration Section */}
              <div className="border border-secondary rounded-lg p-3">
                <div className="border-b border-secondary pb-2 mb-4">
                  <h3 className="text-sm font-medium text-primary">
                    Configuration
                  </h3>
                </div>
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
                          onChange={(e) =>
                            handleConfigUpdate("name", e.target.value)
                          }
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
                                {component.config.model_client &&
                                  onNavigate && (
                                    <Button
                                      type="text"
                                      icon={<Edit className="w-4 h-4" />}
                                      onClick={() =>
                                        onNavigate(
                                          "model",
                                          component.config.model_client
                                            ?.label || "",
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
                        onChange={(e) =>
                          handleConfigUpdate("name", e.target.value)
                        }
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
                          onChange={(e) =>
                            handleConfigUpdate("name", e.target.value)
                          }
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
                            handleConfigUpdate(
                              "downloads_folder",
                              e.target.value
                            )
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
                                        component.config.model_client?.label ||
                                          "",
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
                          checked={
                            component.config.to_save_screenshots || false
                          }
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
                          onChange={(checked) =>
                            handleConfigUpdate("use_ocr", checked)
                          }
                        />
                      </div>
                      <InputWithTooltip
                        label="Browser Channel"
                        tooltip="Channel for the browser (e.g. beta, stable)"
                      >
                        <Input
                          value={component.config.browser_channel || ""}
                          onChange={(e) =>
                            handleConfigUpdate(
                              "browser_channel",
                              e.target.value
                            )
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
                            handleConfigUpdate(
                              "browser_data_dir",
                              e.target.value
                            )
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
              </div>

              {/* Workbench Management Section - Only for AssistantAgent */}
              {isAssistantAgent(component) && (
                <div className="border border-secondary rounded-lg p-3">
                  <div className="border-b border-secondary pb-2 mb-4">
                    <h3 className="text-sm font-medium text-primary">
                      Workbench Management
                    </h3>
                  </div>
                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-primary">
                        Workbenches (
                        {
                          normalizeWorkbenches(component.config.workbench)
                            .length
                        }
                        )
                      </span>
                      <Dropdown
                        menu={{
                          items: [
                            {
                              key: "static",
                              label: (
                                <div>
                                  <div>Static Workbench</div>
                                  <div className="text-xs text-gray-500">
                                    Collection of custom tools
                                  </div>
                                </div>
                              ),
                              icon: <Wrench className="w-4 h-4" />,
                              onClick: addStaticWorkbench,
                            },
                            {
                              type: "divider",
                            },
                            {
                              key: "stdio-mcp",
                              label: (
                                <div>
                                  <div>Stdio MCP Workbench</div>
                                  <div className="text-xs text-gray-500">
                                    Connect to local MCP servers
                                  </div>
                                </div>
                              ),
                              icon: <PlusCircle className="w-4 h-4" />,
                              onClick: addStdioMcpWorkbench,
                            },
                            {
                              key: "sse-mcp",
                              label: (
                                <div>
                                  <div>SSE MCP Workbench</div>
                                  <div className="text-xs text-gray-500">
                                    Connect via Server-Sent Events
                                  </div>
                                </div>
                              ),
                              icon: <PlusCircle className="w-4 h-4" />,
                              onClick: addSseMcpWorkbench,
                            },
                            {
                              key: "streamable-mcp",
                              label: (
                                <div>
                                  <div>Streamable MCP Workbench</div>
                                  <div className="text-xs text-gray-500">
                                    Connect via HTTP streaming
                                  </div>
                                </div>
                              ),
                              icon: <PlusCircle className="w-4 h-4" />,
                              onClick: addStreamableMcpWorkbench,
                            },
                          ],
                        }}
                        trigger={["click"]}
                      >
                        <Button
                          type="dashed"
                          size="small"
                          icon={<PlusCircle className="w-4 h-4" />}
                        >
                          Add Workbench <ChevronDown className="w-3 h-3 ml-1" />
                        </Button>
                      </Dropdown>
                    </div>

                    <div className="space-y-3">
                      {normalizeWorkbenches(component.config.workbench).map(
                        (
                          workbench: Component<WorkbenchConfig>,
                          workbenchIndex: number
                        ) => {
                          // Get tool count for display
                          const getToolCount = () => {
                            if (isStaticWorkbench(workbench)) {
                              return (
                                (workbench.config as StaticWorkbenchConfig)
                                  .tools?.length || 0
                              );
                            }
                            // For MCP workbenches, we don't have a static count
                            return null;
                          };

                          const toolCount = getToolCount();

                          return (
                            <div
                              key={workbenchIndex}
                              className="bg-secondary/30 p-4 rounded-lg border border-gray-200"
                            >
                              {/* Workbench Header */}
                              <div className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  <div>
                                    <div className="flex items-center gap-2">
                                      <span className="text-sm font-medium">
                                        {workbench.label ||
                                          workbench.provider.split(".").pop()}
                                      </span>
                                      {/* Show tool count for static workbenches */}
                                      {toolCount !== null && (
                                        <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                                          {toolCount}{" "}
                                          {toolCount === 1 ? "tool" : "tools"}
                                        </span>
                                      )}
                                      {/* Show MCP indicator for MCP workbenches */}
                                      {isMcpWorkbench(workbench) && (
                                        <span className="text-xs text-blue-600 bg-blue-100 px-2 py-1 rounded">
                                          MCP Server
                                        </span>
                                      )}
                                    </div>
                                    <div className="text-xs text-gray-500 mt-1">
                                      Provider: {workbench.provider}
                                    </div>
                                  </div>
                                </div>
                                <div className="flex items-center gap-2">
                                  {onNavigate && (
                                    <Button
                                      type="text"
                                      icon={<Edit className="w-4 h-4" />}
                                      onClick={() => {
                                        // Navigate to workbench editor with proper index
                                        onNavigate(
                                          "workbench",
                                          workbench.label ||
                                            `workbench-${workbenchIndex}`,
                                          "workbench",
                                          workbenchIndex // Pass the index for proper identification
                                        );
                                      }}
                                    />
                                  )}
                                  <Button
                                    type="text"
                                    danger
                                    icon={<Trash2 className="w-4 h-4" />}
                                    onClick={() => {
                                      const normalizedWorkbenches =
                                        normalizeWorkbenches(
                                          component.config.workbench
                                        );
                                      const updatedWorkbenches = [
                                        ...normalizedWorkbenches,
                                      ];
                                      updatedWorkbenches.splice(
                                        workbenchIndex,
                                        1
                                      );
                                      handleConfigUpdate(
                                        "workbench",
                                        updatedWorkbenches
                                      );
                                    }}
                                  />
                                </div>
                              </div>

                              {/* Show tools for StaticWorkbench */}
                              {isStaticWorkbench(workbench) &&
                                (workbench.config as StaticWorkbenchConfig)
                                  .tools &&
                                (workbench.config as StaticWorkbenchConfig)
                                  .tools.length > 0 && (
                                  <div className="mt-3">
                                    <div className="flex flex-wrap gap-1">
                                      {(
                                        workbench.config as StaticWorkbenchConfig
                                      ).tools.map((tool, toolIndex) => (
                                        <span
                                          key={toolIndex}
                                          className="inline-flex items-center px-2 py-1 rounded-md text-xs font-medium bg-blue-100 text-blue-800 border border-blue-200"
                                        >
                                          <Wrench className="w-3 h-3 mr-1" />
                                          {tool.config.name ||
                                            tool.label ||
                                            `Tool ${toolIndex + 1}`}
                                        </span>
                                      ))}
                                    </div>
                                  </div>
                                )}
                            </div>
                          );
                        }
                      )}

                      {(() => {
                        const workbenches = normalizeWorkbenches(
                          component.config.workbench
                        );
                        return (
                          workbenches.length === 0 && (
                            <div className="text-sm text-secondary text-center bg-secondary/50 p-4 rounded-md">
                              No workbenches configured. Add a workbench to
                              provide tools to this agent.
                            </div>
                          )
                        );
                      })()}
                    </div>
                  </div>
                </div>
              )}
            </>
          ),
        },
      ]}
    />
  );
};

export default React.memo(AgentFields);
