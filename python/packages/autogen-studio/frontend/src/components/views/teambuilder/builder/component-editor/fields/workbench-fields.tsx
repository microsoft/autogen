import React, { useCallback, useState } from "react";
import {
  Input,
  Select,
  Button,
  Space,
  Card,
  Collapse,
  InputNumber,
} from "antd";
import {
  PlusCircle,
  MinusCircle,
  Package,
  Settings,
  Wrench,
  Trash2,
  Info,
  FileText,
} from "lucide-react";
import {
  Component,
  ComponentConfig,
  StaticWorkbenchConfig,
  McpWorkbenchConfig,
  StdioServerParams,
  SseServerParams,
  StreamableHttpServerParams,
  FunctionToolConfig,
} from "../../../../../types/datamodel";
import {
  isStaticWorkbench,
  isMcpWorkbench,
  isFunctionTool,
} from "../../../../../types/guards";
import { ToolFields } from "./tool-fields";
import { McpTestingPanel } from "./mcp-testing-panel";

const { TextArea } = Input;
const { Option } = Select;
const { Panel } = Collapse;

interface WorkbenchFieldsProps {
  component: Component<ComponentConfig>;
  onChange: (updates: Partial<Component<ComponentConfig>>) => void;
  defaultPanelKey?: string[];
}

export const WorkbenchFields: React.FC<WorkbenchFieldsProps> = ({
  component,
  onChange,
  defaultPanelKey = ["details", "configuration"],
}) => {
  const [showAddEnvVar, setShowAddEnvVar] = useState(false);
  const [newEnvVar, setNewEnvVar] = useState({ key: "", value: "" });

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

  if (isStaticWorkbench(component)) {
    const staticConfig = component.config as StaticWorkbenchConfig;

    const handleAddTool = () => {
      const newTool: Component<FunctionToolConfig> = {
        provider: "autogen_core.tools.FunctionTool",
        component_type: "tool",
        version: 1,
        component_version: 1,
        label: "New Tool",
        description: "A new tool",
        config: {
          source_code:
            'def new_tool():\n    """A new tool function"""\n    return "Hello from new tool"',
          name: "new_tool",
          description: "A new tool",
          global_imports: [],
          has_cancellation_support: false,
        },
      };

      const updatedTools = [...(staticConfig.tools || []), newTool];
      handleComponentUpdate({
        config: {
          ...staticConfig,
          tools: updatedTools,
        },
      });
    };

    const handleUpdateTool = (
      index: number,
      updatedTool: Partial<Component<ComponentConfig>>
    ) => {
      const updatedTools = [...(staticConfig.tools || [])];
      updatedTools[index] = {
        ...updatedTools[index],
        ...updatedTool,
      } as Component<any>;
      handleComponentUpdate({
        config: {
          ...staticConfig,
          tools: updatedTools,
        },
      });
    };

    const handleDeleteTool = (index: number) => {
      const updatedTools = [...(staticConfig.tools || [])];
      updatedTools.splice(index, 1);
      handleComponentUpdate({
        config: {
          ...staticConfig,
          tools: updatedTools,
        },
      });
    };

    // Helper function to create dynamic accordion title
    const getComponentDetailsTitle = () => {
      const label = component.label || "";
      const displayName =
        label.length > 20 ? `${label.substring(0, 30)}...` : label;
      return (
        <div className="flex items-center gap-2">
          <Info className="w-4 h-4 text-blue-500" />
          <span className="font-medium">
            Component
            {displayName && (
              <span className="text-gray-500 font-normal ml-2">
                ({displayName})
              </span>
            )}
          </span>
        </div>
      );
    };

    return (
      <div className="space-y-4">
        <Collapse
          defaultActiveKey={defaultPanelKey}
          className="border-0"
          expandIconPosition="end"
          items={[
            {
              key: "details",
              label: getComponentDetailsTitle(),
              children: (
                <div className="space-y-4">
                  <label className="block">
                    <span className="text-sm font-medium text-secondary">
                      Label
                    </span>
                    <Input
                      value={component.label || ""}
                      onChange={(e) =>
                        handleComponentUpdate({ label: e.target.value })
                      }
                      placeholder="Workbench label"
                      className="mt-1"
                    />
                  </label>

                  <label className="block">
                    <span className="text-sm font-medium text-secondary">
                      Description
                    </span>
                    <TextArea
                      value={component.description || ""}
                      onChange={(e) =>
                        handleComponentUpdate({ description: e.target.value })
                      }
                      placeholder="Workbench description"
                      rows={3}
                      className="mt-1"
                    />
                  </label>

                  <div className="grid grid-cols-2 gap-4">
                    <label className="block">
                      <span className="text-sm font-medium text-secondary">
                        Version
                      </span>
                      <InputNumber
                        value={component.version || 1}
                        onChange={(value) =>
                          handleComponentUpdate({ version: value || 1 })
                        }
                        min={1}
                        precision={0}
                        className="w-full mt-1"
                        placeholder="e.g., 1"
                      />
                    </label>

                    <label className="block">
                      <span className="text-sm font-medium text-secondary">
                        Component Version
                      </span>
                      <InputNumber
                        value={component.component_version || 1}
                        onChange={(value) =>
                          handleComponentUpdate({
                            component_version: value || 1,
                          })
                        }
                        min={1}
                        precision={0}
                        className="w-full mt-1"
                        placeholder="e.g., 1"
                      />
                    </label>
                  </div>
                </div>
              ),
            },
            {
              key: "configuration",
              label: (
                <div className="flex items-center gap-2">
                  <Settings className="w-4 h-4 text-green-500" />
                  <span className="font-medium">
                    Static Workbench Configuration
                  </span>
                </div>
              ),
              children: (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm text-gray-600">
                      <Package className="w-4 h-4" />
                      <span>
                        Tools: {staticConfig.tools?.length || 0} configured
                      </span>
                    </div>
                    <Button
                      type="primary"
                      size="small"
                      onClick={handleAddTool}
                      icon={<PlusCircle className="h-4 w-4" />}
                    >
                      Add Tool
                    </Button>
                  </div>

                  {staticConfig.tools && staticConfig.tools.length > 0 ? (
                    <Collapse className="">
                      {staticConfig.tools.map((tool, index) => {
                        if (!isFunctionTool(tool)) return null;

                        return (
                          <Panel
                            key={index}
                            header={
                              <div className="flex items-center justify-between w-full">
                                <div className="flex items-center gap-2">
                                  <Wrench className="w-4 h-4 text-blue-500" />
                                  <span className="font-medium">
                                    {tool.config?.name ||
                                      tool.label ||
                                      "Unnamed Tool"}
                                  </span>
                                  <span className="text-xs text-gray-500 bg-gray-100 px-2 py-1 rounded">
                                    {tool.provider}
                                  </span>
                                </div>
                                {staticConfig.tools!.length > 1 && (
                                  <Button
                                    type="text"
                                    size="small"
                                    danger
                                    onClick={(e) => {
                                      e.stopPropagation(); // Prevent accordion toggle
                                      handleDeleteTool(index);
                                    }}
                                    icon={<Trash2 className="h-4 w-4" />}
                                  />
                                )}
                              </div>
                            }
                          >
                            <ToolFields
                              component={tool}
                              onChange={(updates) =>
                                handleUpdateTool(index, updates)
                              }
                            />
                          </Panel>
                        );
                      })}
                    </Collapse>
                  ) : (
                    <div className="text-center text-gray-500 py-8 border-2 border-dashed border-gray-200 rounded-lg">
                      <Package className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                      <p className="mb-4">No tools configured</p>
                      <Button type="dashed" onClick={handleAddTool}>
                        Add Your First Tool
                      </Button>
                    </div>
                  )}

                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <p className="text-sm text-blue-800">
                      Static workbenches contain a predefined set of tools.
                      Click on a tool above to edit its configuration, or add
                      new tools using the "Add Tool" button.
                    </p>
                  </div>
                </div>
              ),
            },
          ]}
        />
      </div>
    );
  }

  if (isMcpWorkbench(component)) {
    const mcpConfig = component.config as McpWorkbenchConfig;
    const serverParams = mcpConfig.server_params;

    const handleServerParamsUpdate = (
      updates: Partial<typeof serverParams>
    ) => {
      handleComponentUpdate({
        config: {
          ...component.config,
          server_params: {
            ...serverParams,
            ...updates,
          },
        },
      });
    };

    const handleAddEnvVar = () => {
      if (!newEnvVar.key || !newEnvVar.value) return;

      const currentEnv =
        (serverParams.type === "StdioServerParams" && serverParams.env) || {};
      const updatedEnv = {
        ...currentEnv,
        [newEnvVar.key]: newEnvVar.value,
      };

      if (serverParams.type === "StdioServerParams") {
        handleServerParamsUpdate({ env: updatedEnv });
      }

      setNewEnvVar({ key: "", value: "" });
      setShowAddEnvVar(false);
    };

    const handleRemoveEnvVar = (key: string) => {
      if (serverParams.type === "StdioServerParams" && serverParams.env) {
        const updatedEnv = { ...serverParams.env };
        delete updatedEnv[key];
        handleServerParamsUpdate({ env: updatedEnv });
      }
    };

    // Helper function to create dynamic accordion title
    const getComponentDetailsTitle = () => {
      const label = component.label || "";
      const displayName =
        label.length > 30 ? `${label.substring(0, 30)}...` : label;
      return (
        <div className="flex items-center gap-2">
          <Info className="w-4 h-4 text-blue-500" />
          <span className="font-medium">
            Details
            {displayName && (
              <span className="text-gray-500 font-normal ml-2">
                ({displayName})
              </span>
            )}
          </span>
        </div>
      );
    };

    return (
      <div className="space-y-4 scroll">
        <Collapse
          defaultActiveKey={defaultPanelKey}
          className="border-0"
          expandIconPosition="end"
          items={[
            {
              key: "details",
              label: getComponentDetailsTitle(),
              children: (
                <div className="space-y-4">
                  <label className="block">
                    <span className="text-sm font-medium text-secondary">
                      Label
                    </span>
                    <Input
                      value={component.label || ""}
                      onChange={(e) =>
                        handleComponentUpdate({ label: e.target.value })
                      }
                      placeholder="Workbench label"
                      className="mt-1"
                    />
                  </label>

                  <label className="block">
                    <span className="text-sm font-medium text-secondary">
                      Description
                    </span>
                    <TextArea
                      value={component.description || ""}
                      onChange={(e) =>
                        handleComponentUpdate({ description: e.target.value })
                      }
                      placeholder="Workbench description"
                      rows={3}
                      className="mt-1"
                    />
                  </label>

                  <div className="grid grid-cols-2 gap-4">
                    <label className="block">
                      <span className="text-sm font-medium text-secondary">
                        Version
                      </span>
                      <InputNumber
                        value={component.version || 1}
                        onChange={(value) =>
                          handleComponentUpdate({ version: value || 1 })
                        }
                        min={1}
                        precision={0}
                        className="w-full mt-1"
                        placeholder="e.g., 1"
                      />
                    </label>

                    <label className="block">
                      <span className="text-sm font-medium text-secondary">
                        Component Version
                      </span>
                      <InputNumber
                        value={component.component_version || 1}
                        onChange={(value) =>
                          handleComponentUpdate({
                            component_version: value || 1,
                          })
                        }
                        min={1}
                        precision={0}
                        className="w-full mt-1"
                        placeholder="e.g., 1"
                      />
                    </label>
                  </div>
                </div>
              ),
            },
            {
              key: "configuration",
              label: (
                <div className="flex items-center gap-2">
                  <Settings className="w-4 h-4 text-green-500" />
                  <span className="font-medium">Configuration</span>
                </div>
              ),
              children: (
                <div className="space-y-4">
                  <div className="flex items-center gap-2 text-sm text-secondary">
                    <Settings className="w-4 h-4" />
                    <span>Server Type: {serverParams.type}</span>
                  </div>

                  {serverParams.type === "StdioServerParams" && (
                    <>
                      <label className="block">
                        <span className="text-sm font-medium text-primary">
                          Command
                        </span>
                        <Input
                          value={serverParams.command || ""}
                          onChange={(e) =>
                            handleServerParamsUpdate({
                              command: e.target.value,
                            })
                          }
                          placeholder="e.g., uvx"
                          className="mt-1"
                        />
                      </label>

                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm font-medium text-primary">
                            Arguments
                          </span>
                          <Button
                            type="dashed"
                            size="small"
                            icon={<PlusCircle className="w-4 h-4" />}
                            onClick={() => {
                              const currentArgs = serverParams.args || [];
                              handleServerParamsUpdate({
                                args: [...currentArgs, ""],
                              });
                            }}
                          >
                            Add Argument
                          </Button>
                        </div>

                        <div className="space-y-2">
                          {(serverParams.args || []).length === 0 ? (
                            <div className="text-sm text-secondary italic p-3 border border-dashed border-secondary rounded">
                              No arguments. Click "Add Argument" to add command
                              line arguments.
                            </div>
                          ) : (
                            (serverParams.args || []).map((arg, index) => (
                              <div
                                key={index}
                                className="flex items-center gap-2"
                              >
                                <span className="text-xs text-secondary w-8">
                                  {index}
                                </span>
                                <Input
                                  value={arg}
                                  onChange={(e) => {
                                    const newArgs = [
                                      ...(serverParams.args || []),
                                    ];
                                    newArgs[index] = e.target.value;
                                    handleServerParamsUpdate({ args: newArgs });
                                  }}
                                  placeholder={`Argument ${index}`}
                                  className="flex-1"
                                />
                                <Button
                                  type="text"
                                  size="small"
                                  icon={<Trash2 className="w-4 h-4" />}
                                  onClick={() => {
                                    const newArgs = [
                                      ...(serverParams.args || []),
                                    ];
                                    newArgs.splice(index, 1);
                                    handleServerParamsUpdate({ args: newArgs });
                                  }}
                                  className="text-red-500 hover:text-red-700"
                                />
                              </div>
                            ))
                          )}
                        </div>

                        {(serverParams.args || []).length > 0 && (
                          <div className="text-xs text-secondary bg-secondary/30 p-2 rounded">
                            <strong>Command preview:</strong>{" "}
                            {serverParams.command}{" "}
                            {(serverParams.args || []).join(" ")}
                          </div>
                        )}
                      </div>

                      <label className="block">
                        <span className="text-sm font-medium text-primary">
                          Read Timeout (seconds)
                        </span>
                        <Input
                          type="number"
                          value={serverParams.read_timeout_seconds || 5}
                          onChange={(e) =>
                            handleServerParamsUpdate({
                              read_timeout_seconds:
                                parseFloat(e.target.value) || 5,
                            })
                          }
                          className="mt-1"
                        />
                      </label>

                      <div className="space-y-2">
                        <span className="text-sm font-medium text-primary">
                          Environment Variables
                        </span>

                        {serverParams.env &&
                          Object.keys(serverParams.env).length > 0 && (
                            <div className="space-y-2">
                              {Object.entries(serverParams.env).map(
                                ([key, value]) => (
                                  <div
                                    key={key}
                                    className="flex items-center gap-2 bg-gray-50 rounded px-3 py-2"
                                  >
                                    <span className="font-mono text-sm flex-1">
                                      {key}={value}
                                    </span>
                                    <Button
                                      type="text"
                                      size="small"
                                      onClick={() => handleRemoveEnvVar(key)}
                                      icon={<MinusCircle className="h-4 w-4" />}
                                    />
                                  </div>
                                )
                              )}
                            </div>
                          )}

                        {showAddEnvVar ? (
                          <div className="border rounded p-3 space-y-3">
                            <Space>
                              <Input
                                placeholder="Variable name"
                                value={newEnvVar.key}
                                onChange={(e) =>
                                  setNewEnvVar((prev) => ({
                                    ...prev,
                                    key: e.target.value,
                                  }))
                                }
                              />
                              <Input
                                placeholder="Variable value"
                                value={newEnvVar.value}
                                onChange={(e) =>
                                  setNewEnvVar((prev) => ({
                                    ...prev,
                                    value: e.target.value,
                                  }))
                                }
                                onKeyDown={(e) => {
                                  if (
                                    e.key === "Enter" &&
                                    newEnvVar.key &&
                                    newEnvVar.value
                                  ) {
                                    handleAddEnvVar();
                                  }
                                }}
                              />
                              <Button
                                onClick={handleAddEnvVar}
                                disabled={!newEnvVar.key || !newEnvVar.value}
                              >
                                Add
                              </Button>
                            </Space>
                          </div>
                        ) : (
                          <Button
                            type="dashed"
                            onClick={() => setShowAddEnvVar(true)}
                            className="w-full"
                          >
                            <PlusCircle className="h-4 w-4 mr-2" />
                            Add Environment Variable
                          </Button>
                        )}
                      </div>
                    </>
                  )}

                  {serverParams.type === "SseServerParams" && (
                    <>
                      <label className="block">
                        <span className="text-sm font-medium text-primary">
                          Server URL
                        </span>
                        <Input
                          value={serverParams.url || ""}
                          onChange={(e) =>
                            handleServerParamsUpdate({ url: e.target.value })
                          }
                          placeholder="https://your-mcp-server.com"
                          className="mt-1"
                        />
                      </label>

                      <label className="block">
                        <span className="text-sm font-medium text-primary">
                          Timeout (seconds)
                        </span>
                        <Input
                          type="number"
                          value={serverParams.timeout || 5}
                          onChange={(e) =>
                            handleServerParamsUpdate({
                              timeout: parseFloat(e.target.value) || 5,
                            })
                          }
                          className="mt-1"
                        />
                      </label>

                      <label className="block">
                        <span className="text-sm font-medium text-primary">
                          SSE Read Timeout (seconds)
                        </span>
                        <Input
                          type="number"
                          value={serverParams.sse_read_timeout || 300}
                          onChange={(e) =>
                            handleServerParamsUpdate({
                              sse_read_timeout:
                                parseFloat(e.target.value) || 300,
                            })
                          }
                          className="mt-1"
                        />
                      </label>
                    </>
                  )}

                  {serverParams.type === "StreamableHttpServerParams" && (
                    <>
                      <label className="block">
                        <span className="text-sm font-medium text-secondary">
                          Server URL
                        </span>
                        <Input
                          type="url"
                          value={serverParams.url || ""}
                          onChange={(e) =>
                            handleServerParamsUpdate({ url: e.target.value })
                          }
                          placeholder="https://your-streamable-http-server.com"
                          className="mt-1"
                        />
                      </label>

                      <label className="block">
                        <span className="text-sm font-medium text-primary">
                          Timeout (seconds)
                        </span>
                        <Input
                          type="number"
                          value={serverParams.timeout || 30}
                          onChange={(e) =>
                            handleServerParamsUpdate({
                              timeout: parseFloat(e.target.value) || 30,
                            })
                          }
                          className="mt-1"
                        />
                      </label>

                      <label className="block">
                        <span className="text-sm font-medium text-primary">
                          SSE Read Timeout (seconds)
                        </span>
                        <Input
                          type="number"
                          value={serverParams.sse_read_timeout || 300}
                          onChange={(e) =>
                            handleServerParamsUpdate({
                              sse_read_timeout:
                                parseFloat(e.target.value) || 300,
                            })
                          }
                          className="mt-1"
                        />
                      </label>

                      <label className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={serverParams.terminate_on_close ?? true}
                          onChange={(e) =>
                            handleServerParamsUpdate({
                              terminate_on_close: e.target.checked,
                            })
                          }
                          className="rounded"
                        />
                        <span className="text-sm font-medium text-primary">
                          Terminate on Close
                        </span>
                      </label>
                    </>
                  )}

                  <div className="bg-secondary/30 border border-secondary rounded-lg p-4">
                    <p className="text-sm text-secondary">
                      {serverParams.type === "StreamableHttpServerParams"
                        ? "Streamable HTTP workbenches connect to MCP servers over HTTP with streaming capabilities, ideal for cloud-based services and web APIs."
                        : "MCP (Model Context Protocol) workbenches connect to external tool servers that provide dynamic tool capabilities. The tools available depend on what the MCP server provides at runtime."}
                    </p>
                  </div>
                </div>
              ),
            },
            {
              key: "testing",
              label: (
                <div className="flex items-center gap-2">
                  <FileText className="w-4 h-4 text-purple-500" />
                  <span className="font-medium">MCP Testing Panel</span>
                </div>
              ),
              children: (
                <>
                  <McpTestingPanel serverParams={serverParams} />
                </>
              ),
            },
          ]}
        />
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="text-center text-gray-500 py-8">
        <Package className="w-12 h-12 mx-auto mb-4 text-gray-400" />
        <p>Unknown workbench type</p>
      </div>
    </div>
  );
};

export default React.memo(WorkbenchFields);
