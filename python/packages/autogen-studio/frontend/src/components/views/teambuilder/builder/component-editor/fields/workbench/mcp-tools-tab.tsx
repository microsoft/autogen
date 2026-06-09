import React, { useState, useCallback, useEffect, useRef } from "react";
import {
  Button,
  Form,
  Input,
  Typography,
  Space,
  Alert,
  Tag,
  Spin,
  Card,
  Select,
  Divider,
  Dropdown,
  MenuProps,
  Image,
  Collapse,
} from "antd";
import {
  PlayCircle,
  Wrench,
  CheckCircle,
  Search,
  ChevronDown,
  Shield,
  AlertTriangle,
  RotateCcw,
  Globe,
  Hash,
  FileText,
  Image as ImageIcon,
  Code,
  Eye,
  EyeOff,
} from "lucide-react";
import { McpServerParams } from "../../../../../../types/datamodel";
import {
  Tool,
  CallToolResult,
  McpWebSocketClient,
  ServerCapabilities,
} from "../../../../../mcp/api";

const { TextArea } = Input;
const { Text } = Typography;
const { Option } = Select;

interface McpToolsTabProps {
  serverParams: McpServerParams;
  wsClient: McpWebSocketClient | null;
  connected: boolean;
  capabilities: ServerCapabilities | null;
}

const McpToolsTabComponent: React.FC<McpToolsTabProps> = ({
  serverParams,
  wsClient,
  connected,
  capabilities,
}) => {
  const [tools, setTools] = useState<Tool[]>([]);
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null);
  const [toolArguments, setToolArguments] = useState<Record<string, any>>({});
  const [loadingTools, setLoadingTools] = useState(false);
  const [executingTool, setExecutingTool] = useState(false);
  const [toolResult, setToolResult] = useState<CallToolResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingError, setLoadingError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [resultView, setResultView] = useState<"raw" | "parsed">("parsed");
  const runToolRef = useRef<HTMLDivElement>(null);
  const toolResultRef = useRef<HTMLDivElement>(null);

  // Auto-select first tool when tools are loaded
  useEffect(() => {
    if (tools.length > 0 && !selectedTool) {
      const firstTool = tools[0];
      setSelectedTool(firstTool);
      setToolResult(null);

      // Initialize tool arguments with default values based on schema
      const initialArgs: Record<string, any> = {};
      const schema = firstTool.inputSchema;
      const properties = schema?.properties || {};

      Object.entries(properties).forEach(([key, propSchema]: [string, any]) => {
        if (propSchema.default !== undefined) {
          initialArgs[key] = propSchema.default;
        }
      });

      setToolArguments(initialArgs);
    }
  }, [tools, selectedTool]);

  // Auto-scroll to run tool when arguments form is shown
  useEffect(() => {
    if (selectedTool && runToolRef.current) {
      setTimeout(() => {
        runToolRef.current?.scrollIntoView({
          behavior: "smooth",
          block: "nearest",
        });
      }, 100);
    }
  }, [selectedTool]);

  // Auto-scroll to tool result when it appears
  useEffect(() => {
    if (toolResult && toolResultRef.current) {
      setTimeout(() => {
        toolResultRef.current?.scrollIntoView({
          behavior: "smooth",
          block: "nearest",
        });
      }, 100);
    }
  }, [toolResult]);

  const handleListTools = useCallback(
    async (clearResults: boolean = false) => {
      if (!connected) {
        setLoadingError("WebSocket not connected");
        return;
      }

      if (!wsClient) {
        setLoadingError("WebSocket client not initialized");
        return;
      }

      setLoadingTools(true);
      setLoadingError(null);

      // Only clear selected tool and results when explicitly requested (e.g., reconnection)
      if (clearResults) {
        setSelectedTool(null);
        setToolResult(null);
        setToolArguments({});
      }

      try {
        const result = await wsClient.executeOperation({
          operation: "list_tools",
        });

        if (result?.tools) {
          setTools(result.tools);
        } else {
          setLoadingError("No tools received from server");
        }
      } catch (err: any) {
        setLoadingError(`Failed to fetch tools: ${err.message}`);
      } finally {
        setLoadingTools(false);
      }
    },
    [connected]
  );

  // Wrapper for UI button clicks that should clear results
  const handleRefreshTools = useCallback(() => {
    handleListTools(true);
  }, [handleListTools]);

  // Load tools when connected and capabilities indicate tools are available
  // Use a ref to track if we've already loaded tools to prevent unnecessary reloads
  const hasLoadedToolsRef = useRef(false);

  useEffect(() => {
    console.log(
      "Tools useEffect triggered - connected:",
      connected,
      "capabilities?.tools:",
      !!capabilities?.tools,
      "wsClient:",
      !!wsClient,
      "hasLoaded:",
      hasLoadedToolsRef.current
    );

    if (
      connected &&
      capabilities?.tools &&
      wsClient &&
      !hasLoadedToolsRef.current
    ) {
      console.log("Loading tools for the first time");
      hasLoadedToolsRef.current = true;
      handleListTools();
    } else if (!connected || !capabilities?.tools) {
      // Reset the flag when disconnected or tools capability is removed
      console.log(
        "Resetting hasLoadedToolsRef due to disconnection or no tools capability"
      );
      hasLoadedToolsRef.current = false;
    }
  }, [connected, capabilities?.tools, handleListTools]);

  const handleExecuteTool = useCallback(async () => {
    if (!selectedTool || !connected || !wsClient) return;

    // Clear activity messages for this new operation
    if (wsClient.clearActivityMessages) {
      wsClient.clearActivityMessages();
    }

    setExecutingTool(true);
    setError(null);
    setToolResult(null);

    try {
      const result = await wsClient.executeOperation({
        operation: "call_tool",
        tool_name: selectedTool.name,
        arguments: toolArguments,
      });

      if (result?.result) {
        setToolResult(result.result);
      } else {
        setError("No result received from tool execution");
      }
    } catch (err: any) {
      setError(`Failed to execute tool: ${err.message}`);
    } finally {
      setExecutingTool(false);
    }
  }, [connected, selectedTool, toolArguments, wsClient]);

  // Filter tools based on search query
  const filteredTools = tools.filter((tool) => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    const displayName = (tool.annotations?.title || tool.name).toLowerCase();
    const description = (tool.description || "").toLowerCase();
    return displayName.includes(query) || description.includes(query);
  });

  // Helper function to get tool display name
  const getToolDisplayName = (tool: Tool): string => {
    return tool.annotations?.title || tool.name;
  };

  // Helper function to get parameter count
  const getParameterCount = (tool: Tool): number => {
    return Object.keys(tool.inputSchema?.properties || {}).length;
  };

  // Handle tool selection from dropdown
  const handleMenuClick: MenuProps["onClick"] = (e) => {
    const toolName = e.key;
    const tool = tools.find((t) => t.name === toolName);
    if (tool) {
      handleToolSelect(tool);
    }
  };

  // Handle tool selection
  const handleToolSelect = (tool: Tool) => {
    setSelectedTool(tool);
    setToolResult(null);

    // Initialize tool arguments with default values based on schema
    const initialArgs: Record<string, any> = {};
    const schema = tool.inputSchema;
    const properties = schema?.properties || {};

    Object.entries(properties).forEach(([key, propSchema]: [string, any]) => {
      if (propSchema.default !== undefined) {
        initialArgs[key] = propSchema.default;
      }
    });

    setToolArguments(initialArgs);
  };

  // Render MCP result content based on MIME type
  const renderMCPResult = (content: any, index: number) => {
    const { type, text, data, mimeType } = content;

    // Helper function to check if data is base64 encoded
    const isBase64 = (str: string) => {
      try {
        return btoa(atob(str)) === str;
      } catch (err) {
        return false;
      }
    };

    // Helper function to format JSON
    const formatJSON = (jsonString: string) => {
      try {
        const parsed = JSON.parse(jsonString);
        return JSON.stringify(parsed, null, 2);
      } catch {
        return jsonString;
      }
    };

    // Render based on MIME type
    const renderContent = () => {
      // Handle images
      if (mimeType?.startsWith("image/")) {
        if (data && isBase64(data)) {
          return (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <ImageIcon size={16} />
                <Text strong>Image</Text>
                <Tag color="green">{mimeType}</Tag>
              </div>
              <Image
                src={`data:${mimeType};base64,${data}`}
                alt="MCP Result Image"
                style={{ maxWidth: "300px", maxHeight: "300px" }}
                placeholder={<div>Loading image...</div>}
              />
            </div>
          );
        }
      }

      // Handle JSON content
      if (
        mimeType === "application/json" ||
        (type === "text" &&
          text &&
          (text.trim().startsWith("{") || text.trim().startsWith("[")))
      ) {
        const jsonContent = text || data;
        const formattedJson = formatJSON(jsonContent);

        return (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Code size={16} />
              <Text strong>JSON Data</Text>
              <Tag color="purple">application/json</Tag>
            </div>
            <Collapse size="small" ghost defaultActiveKey={["json"]}>
              <Collapse.Panel
                header={
                  <div className="flex items-center gap-2">
                    <Text type="secondary">View formatted JSON</Text>
                  </div>
                }
                key="json"
              >
                <pre
                  className="bg-secondary text-primary"
                  style={{
                    padding: "12px",
                    borderRadius: "6px",
                    fontSize: "12px",
                    lineHeight: "1.4",
                    overflow: "auto",
                    maxHeight: "300px",
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    overflowWrap: "break-word",
                    margin: 0,
                    border: "1px solid var(--border-color, #e1e4e8)",
                  }}
                >
                  {formattedJson}
                </pre>
              </Collapse.Panel>
            </Collapse>
          </div>
        );
      }

      // Handle text content
      if (type === "text") {
        const textContent = text || data || "";
        return (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <FileText size={16} />
              <Text strong>Text Content</Text>
              {mimeType && <Tag color="blue">{mimeType}</Tag>}
            </div>
            {textContent ? (
              <pre
                className="bg-secondary text-primary"
                style={{
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                  padding: "12px",
                  borderRadius: "6px",
                  fontSize: "13px",
                  lineHeight: "1.5",
                  maxHeight: "400px",
                  overflow: "auto",
                  margin: 0,
                }}
              >
                {textContent}
              </pre>
            ) : (
              <Text type="secondary" className="italic">
                Empty text content
              </Text>
            )}
          </div>
        );
      }

      // Handle binary/data content
      if (data) {
        const dataPreview =
          data.length > 100 ? `${data.substring(0, 100)}...` : data;

        return (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Code size={16} />
              <Text strong>Binary Data</Text>
              {mimeType && <Tag color="orange">{mimeType}</Tag>}
              <Tag color="default">{data.length} bytes</Tag>
            </div>
            <Collapse size="small" ghost>
              <Collapse.Panel
                header={
                  <div className="flex items-center gap-2">
                    <Eye size={14} />
                    <Text type="secondary">View raw data (preview)</Text>
                  </div>
                }
                key="data"
              >
                <pre
                  className="bg-secondary text-primary"
                  style={{
                    padding: "12px",
                    borderRadius: "6px",
                    fontSize: "11px",
                    lineHeight: "1.4",
                    overflow: "auto",
                    maxHeight: "200px",
                    border: "1px solid var(--border-color, #e1e4e8)",
                    fontFamily: "monospace",
                    wordBreak: "break-all",
                  }}
                >
                  {dataPreview}
                </pre>
              </Collapse.Panel>
            </Collapse>
          </div>
        );
      }

      // Fallback for unknown content types
      return (
        <div>
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={16} />
            <Text strong>Unknown Content</Text>
            <Tag color="default">{type}</Tag>
            {mimeType && <Tag color="gray">{mimeType}</Tag>}
          </div>
          <Text type="secondary">
            No suitable renderer found for this content type.
          </Text>
        </div>
      );
    };

    return (
      <Card
        key={index}
        size="small"
        className="bg-secondary"
        style={{
          border: "1px solid var(--border-color, #e8e8e8)",
        }}
      >
        {renderContent()}
      </Card>
    );
  };

  const renderToolSelector = () => {
    if (loadingTools) {
      return (
        <Card size="small" title="Available Tools">
          <div style={{ textAlign: "center", padding: "24px" }}>
            <Spin size="large" />
            <div style={{ marginTop: "16px" }}>
              <Text>Loading tools...</Text>
            </div>
          </div>
        </Card>
      );
    }

    if (tools.length === 0) {
      return (
        <Card size="small" title="Available Tools">
          <Space direction="vertical" style={{ width: "100%" }}>
            <Button
              type="primary"
              onClick={handleRefreshTools}
              icon={<Wrench size={16} />}
            >
              Load Tools
            </Button>

            {loadingError && (
              <Alert
                type="error"
                message="Failed to Load Tools"
                description={loadingError}
                action={
                  <Space>
                    <Button
                      size="small"
                      onClick={handleRefreshTools}
                      loading={loadingTools}
                    >
                      Retry
                    </Button>
                    <Button size="small" onClick={() => setLoadingError(null)}>
                      Clear
                    </Button>
                  </Space>
                }
                showIcon
              />
            )}
          </Space>
        </Card>
      );
    }

    // Create dropdown menu items
    const items: MenuProps["items"] = [
      {
        type: "group",
        label: (
          <div>
            <div className="text-xs text-secondary mb-1">Select a tool</div>
            <Input
              prefix={<Search className="w-4 h-4" />}
              placeholder="Search tools..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onClick={(e) => e.stopPropagation()}
            />
          </div>
        ),
        key: "search-tools",
      },
      {
        type: "divider",
      },
      ...filteredTools.map((tool) => {
        const displayName = getToolDisplayName(tool);
        const paramCount = getParameterCount(tool);
        const truncatedDescription =
          tool.description && tool.description.length > 50
            ? `${tool.description.substring(0, 50)}...`
            : tool.description || "No description available";

        return {
          label: (
            <div>
              <div className="flex items-center justify-between">
                <span className="font-medium">{displayName}</span>
                <div className="flex items-center gap-1 text-xs text-secondary">
                  <Hash size={12} />
                  <span>{paramCount}</span>
                </div>
              </div>
              <div className="text-xs text-secondary mt-1">
                {truncatedDescription}
              </div>
            </div>
          ),
          key: tool.name,
          icon: <Wrench className="w-4 h-4" />,
        };
      }),
    ];

    const menuProps = {
      items,
      onClick: handleMenuClick,
    };

    return (
      <Card
        size="small"
        title={
          <Space style={{ width: "100%", justifyContent: "space-between" }}>
            <span>Available Tools ({tools.length})</span>
            <Button
              type="link"
              size="small"
              onClick={handleRefreshTools}
              loading={loadingTools}
              icon={<Wrench size={12} />}
            >
              Refresh
            </Button>
          </Space>
        }
      >
        <Space direction="vertical" style={{ width: "100%" }} size="middle">
          <Dropdown.Button
            menu={menuProps}
            type="default"
            className="w-full"
            placement="bottomLeft"
            icon={<ChevronDown className="w-4 h-4" />}
            disabled={loadingTools}
          >
            <div className="flex items-center gap-2">
              <Wrench className="w-4 h-4" />
              <span>
                {selectedTool
                  ? getToolDisplayName(selectedTool)
                  : "Select a tool"}
              </span>
            </div>
          </Dropdown.Button>

          {selectedTool && (
            <div className="p-3 bg-secondary rounded border">
              <div className="flex items-center gap-2 mb-2">
                <Wrench size={16} />
                <Text strong>{getToolDisplayName(selectedTool)}</Text>
                <Tag color="blue">{getParameterCount(selectedTool)} params</Tag>
              </div>
              {/* Annotations on their own line, inline and wrapping if needed */}
              <div className="flex flex-wrap gap-1 mb-2">
                {selectedTool.annotations?.readOnlyHint && (
                  <div className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-green-50 text-green-700 border border-green-200">
                    Read-only
                  </div>
                )}
                {selectedTool.annotations?.destructiveHint && (
                  <div className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-red-50 text-red-700 border border-red-200">
                    Destructive
                  </div>
                )}
                {selectedTool.annotations?.idempotentHint && (
                  <div className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-purple-50 text-purple-700 border border-purple-200">
                    Idempotent
                  </div>
                )}
                {selectedTool.annotations?.openWorldHint && (
                  <div className="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-orange-50 text-orange-700 border border-orange-200">
                    Open-world
                  </div>
                )}
              </div>
              {selectedTool.description && (
                <Text type="secondary" className="text-sm">
                  {selectedTool.description}
                </Text>
              )}
            </div>
          )}
        </Space>
      </Card>
    );
  };

  const renderArgumentsForm = () => {
    if (!selectedTool) return null;

    const schema = selectedTool.inputSchema;
    const properties = schema?.properties || {};
    const required = schema?.required || [];

    return (
      <Card size="small" title={`Run ${selectedTool.name} Tool`}>
        <Space direction="vertical" style={{ width: "100%" }}>
          {selectedTool.description && (
            <Text type="secondary">{selectedTool.description}</Text>
          )}

          <Form layout="vertical">
            {Object.entries(properties).map(
              ([key, propSchema]: [string, any]) => (
                <Form.Item
                  key={key}
                  label={
                    <Space>
                      <Text>{key}</Text>
                      {required.includes(key) && (
                        <Tag color="red">Required</Tag>
                      )}
                    </Space>
                  }
                >
                  {propSchema.type === "string" && propSchema.enum ? (
                    <Select
                      style={{ width: "100%" }}
                      placeholder={`Select ${key}`}
                      value={toolArguments[key]}
                      onChange={(value) =>
                        setToolArguments({ ...toolArguments, [key]: value })
                      }
                    >
                      {propSchema.enum.map((option: string) => (
                        <Option key={option} value={option}>
                          {option}
                        </Option>
                      ))}
                    </Select>
                  ) : propSchema.type === "object" ||
                    propSchema.type === "array" ? (
                    <TextArea
                      placeholder={`Enter ${key} as JSON`}
                      rows={3}
                      value={
                        toolArguments[key]
                          ? JSON.stringify(toolArguments[key], null, 2)
                          : ""
                      }
                      onChange={(e) => {
                        try {
                          const parsed = JSON.parse(e.target.value);
                          setToolArguments({ ...toolArguments, [key]: parsed });
                        } catch {
                          // Keep the raw string for now, user might still be typing
                          setToolArguments({
                            ...toolArguments,
                            [key]: e.target.value,
                          });
                        }
                      }}
                    />
                  ) : propSchema.type === "boolean" ? (
                    <Select
                      style={{ width: "100%" }}
                      placeholder={`Select ${key}`}
                      value={toolArguments[key]}
                      onChange={(value) =>
                        setToolArguments({ ...toolArguments, [key]: value })
                      }
                    >
                      <Option value={true}>True</Option>
                      <Option value={false}>False</Option>
                    </Select>
                  ) : (
                    <Input
                      type={
                        propSchema.type === "number" ||
                        propSchema.type === "integer"
                          ? "number"
                          : "text"
                      }
                      placeholder={propSchema.description || `Enter ${key}`}
                      value={toolArguments[key] || ""}
                      onChange={(e) => {
                        let value: any = e.target.value;

                        // Convert to appropriate type based on schema
                        if (propSchema.type === "integer") {
                          if (value === "") {
                            value = undefined;
                          } else {
                            const intValue = parseInt(value, 10);
                            value = isNaN(intValue) ? value : intValue; // Keep as string if invalid
                          }
                        } else if (propSchema.type === "number") {
                          if (value === "") {
                            value = undefined;
                          } else {
                            const floatValue = parseFloat(value);
                            value = isNaN(floatValue) ? value : floatValue; // Keep as string if invalid
                          }
                        }
                        // Keep strings as-is, booleans are handled separately

                        setToolArguments({
                          ...toolArguments,
                          [key]: value,
                        });
                      }}
                    />
                  )}
                  {propSchema.description && (
                    <Text type="secondary" style={{ fontSize: "12px" }}>
                      {propSchema.description}
                    </Text>
                  )}
                  {(propSchema.type === "integer" ||
                    propSchema.type === "number") && (
                    <Text
                      type="secondary"
                      style={{ fontSize: "11px", fontStyle: "italic" }}
                    >
                      Expected: {propSchema.type} | Current:{" "}
                      {typeof toolArguments[key]} | Value:{" "}
                      {JSON.stringify(toolArguments[key])}
                    </Text>
                  )}
                </Form.Item>
              )
            )}
          </Form>

          <div ref={runToolRef}>
            <Button
              type="primary"
              icon={<PlayCircle size={16} />}
              onClick={handleExecuteTool}
              loading={executingTool}
              style={{ width: "100%" }}
            >
              {executingTool ? "Executing..." : "Run Tool"}
            </Button>
          </div>
        </Space>
      </Card>
    );
  };

  const renderToolResult = () => {
    if (!toolResult) return null;

    return (
      <Card
        size="small"
        className="bg-secondary"
        title={
          <Space>
            <CheckCircle size={16} color="green" />
            Tool Result
            <Tag color="green">
              {toolResult.content.length} item
              {toolResult.content.length !== 1 ? "s" : ""}
            </Tag>
          </Space>
        }
      >
        <div ref={toolResultRef}>
          <Space direction="vertical" style={{ width: "100%" }}>
            {toolResult.content.map((content, index) =>
              renderMCPResult(content, index)
            )}
          </Space>
        </div>
      </Card>
    );
  };

  return (
    <div style={{ width: "100%", maxWidth: "100%", overflow: "hidden" }}>
      <Space direction="vertical" style={{ width: "100%" }}>
        {renderToolSelector()}
        {selectedTool && !loadingTools && !loadingError && (
          <>
            <Divider />
            {renderArgumentsForm()}
          </>
        )}
        {error && (
          <Alert
            type="error"
            message="Tool Operation Error"
            description={error}
            action={
              <Space>
                <Button size="small" onClick={() => setError(null)}>
                  Clear Error
                </Button>
                {selectedTool && (
                  <Button
                    size="small"
                    type="primary"
                    onClick={handleExecuteTool}
                    loading={executingTool}
                  >
                    Retry
                  </Button>
                )}
              </Space>
            }
            showIcon
          />
        )}
        {toolResult && !loadingTools && !loadingError && (
          <>
            <Divider />
            {renderToolResult()}
          </>
        )}
      </Space>
    </div>
  );
};

// Custom comparison function to prevent unnecessary re-renders
const arePropsEqual = (
  prevProps: McpToolsTabProps,
  nextProps: McpToolsTabProps
): boolean => {
  // Only re-render if connection state, capabilities, or serverParams change
  return (
    prevProps.connected === nextProps.connected &&
    prevProps.capabilities === nextProps.capabilities &&
    // Compare serverParams by JSON stringifying (deep comparison)
    JSON.stringify(prevProps.serverParams) ===
      JSON.stringify(nextProps.serverParams) &&
    // Don't compare wsClient directly as it might be recreated, but compare its existence
    !!prevProps.wsClient === !!nextProps.wsClient
  );
};

export const McpToolsTab = React.memo(McpToolsTabComponent, arePropsEqual);
