import React, { useCallback, useState } from "react";
import { Input, Select, Button, Space, Card } from "antd";
import { PlusCircle, MinusCircle, Package, Settings } from "lucide-react";
import {
  Component,
  ComponentConfig,
  StaticWorkbenchConfig,
  McpWorkbenchConfig,
  StdioServerParams,
  SseServerParams,
  StreamableHttpServerParams,
} from "../../../../../types/datamodel";
import { isStaticWorkbench, isMcpWorkbench } from "../../../../../types/guards";
import DetailGroup from "../detailgroup";

const { TextArea } = Input;
const { Option } = Select;

interface WorkbenchFieldsProps {
  component: Component<ComponentConfig>;
  onChange: (updates: Partial<Component<ComponentConfig>>) => void;
}

export const WorkbenchFields: React.FC<WorkbenchFieldsProps> = ({
  component,
  onChange,
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
    return (
      <div className="space-y-6">
        <DetailGroup title="Static Workbench Configuration">
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Package className="w-4 h-4" />
              <span>
                Tools: {component.config.tools?.length || 0} configured
              </span>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm text-blue-800">
                Static workbenches contain a predefined set of tools. Tools are
                managed by dragging and dropping them onto agent nodes in the
                visual builder.
              </p>
            </div>

            {component.config.tools && component.config.tools.length > 0 && (
              <div className="space-y-2">
                <span className="text-sm font-medium text-gray-700">
                  Configured Tools
                </span>
                <div className="space-y-2">
                  {component.config.tools.map((tool, index) => (
                    <Card key={index} size="small" className="bg-gray-50">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-medium text-sm">
                            {tool.label || tool.config?.name || "Unnamed Tool"}
                          </div>
                          <div className="text-xs text-gray-500">
                            {tool.provider}
                          </div>
                        </div>
                        <div className="text-xs text-gray-400">
                          {tool.component_type}
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              </div>
            )}
          </div>
        </DetailGroup>
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

    return (
      <div className="space-y-6">
        <DetailGroup title="MCP Workbench Configuration">
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Settings className="w-4 h-4" />
              <span>Server Type: {serverParams.type}</span>
            </div>

            {serverParams.type === "StdioServerParams" && (
              <>
                <label className="block">
                  <span className="text-sm font-medium text-gray-700">
                    Command
                  </span>
                  <Input
                    value={serverParams.command || ""}
                    onChange={(e) =>
                      handleServerParamsUpdate({ command: e.target.value })
                    }
                    placeholder="e.g., uvx"
                    className="mt-1"
                  />
                </label>

                <label className="block">
                  <span className="text-sm font-medium text-gray-700">
                    Arguments (one per line)
                  </span>
                  <TextArea
                    value={(serverParams.args || []).join("\n")}
                    onChange={(e) =>
                      handleServerParamsUpdate({
                        args: e.target.value
                          .split("\n")
                          .map((line) => line.trim())
                          .filter((line) => line),
                      })
                    }
                    placeholder="mcp-server-fetch"
                    rows={3}
                    className="mt-1"
                  />
                </label>

                <label className="block">
                  <span className="text-sm font-medium text-gray-700">
                    Read Timeout (seconds)
                  </span>
                  <Input
                    type="number"
                    value={serverParams.read_timeout_seconds || 5}
                    onChange={(e) =>
                      handleServerParamsUpdate({
                        read_timeout_seconds: parseFloat(e.target.value) || 5,
                      })
                    }
                    className="mt-1"
                  />
                </label>

                <div className="space-y-2">
                  <span className="text-sm font-medium text-gray-700">
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
                  <span className="text-sm font-medium text-gray-700">
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
                  <span className="text-sm font-medium text-gray-700">
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
                  <span className="text-sm font-medium text-gray-700">
                    SSE Read Timeout (seconds)
                  </span>
                  <Input
                    type="number"
                    value={serverParams.sse_read_timeout || 300}
                    onChange={(e) =>
                      handleServerParamsUpdate({
                        sse_read_timeout: parseFloat(e.target.value) || 300,
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
                  <span className="text-sm font-medium text-gray-700">
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
                  <span className="text-sm font-medium text-gray-700">
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
                  <span className="text-sm font-medium text-gray-700">
                    SSE Read Timeout (seconds)
                  </span>
                  <Input
                    type="number"
                    value={serverParams.sse_read_timeout || 300}
                    onChange={(e) =>
                      handleServerParamsUpdate({
                        sse_read_timeout: parseFloat(e.target.value) || 300,
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
                  <span className="text-sm font-medium text-gray-700">
                    Terminate on Close
                  </span>
                </label>
              </>
            )}

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <p className="text-sm text-blue-800">
                {serverParams.type === "StreamableHttpServerParams" 
                  ? "Streamable HTTP workbenches connect to MCP servers over HTTP with streaming capabilities, ideal for cloud-based services and web APIs."
                  : "MCP (Model Context Protocol) workbenches connect to external tool servers that provide dynamic tool capabilities. The tools available depend on what the MCP server provides at runtime."
                }
              </p>
            </div>
          </div>
        </DetailGroup>
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
