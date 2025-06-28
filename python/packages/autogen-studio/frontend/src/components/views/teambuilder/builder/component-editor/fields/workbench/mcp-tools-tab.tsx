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
} from "lucide-react";
import { McpServerParams } from "../../../../../../types/datamodel";
import { mcpAPI, Tool, CallToolResult } from "../../../../../mcp/api";

const { TextArea } = Input;
const { Text } = Typography;
const { Option } = Select;

interface McpToolsTabProps {
  serverParams: McpServerParams;
}

export const McpToolsTab: React.FC<McpToolsTabProps> = ({ serverParams }) => {
  const [tools, setTools] = useState<Tool[]>([]);
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null);
  const [toolArguments, setToolArguments] = useState<Record<string, any>>({});
  const [loadingTools, setLoadingTools] = useState(false);
  const [executingTool, setExecutingTool] = useState(false);
  const [toolResult, setToolResult] = useState<CallToolResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState<string>("");
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

  const handleListTools = useCallback(async () => {
    setLoadingTools(true);
    setError(null);
    // Clear selected tool and results when loading new tools
    setSelectedTool(null);
    setToolResult(null);
    setToolArguments({});

    try {
      const result = await mcpAPI.listTools(serverParams);

      console.log("Fetched tools:", result);

      if (result.status) {
        setTools(result.tools || []);
      } else {
        setError(result.message);
      }
    } catch (err: any) {
      setError(`Failed to fetch tools: ${err.message}`);
    } finally {
      setLoadingTools(false);
    }
  }, [serverParams]);

  // Load tools on mount
  useEffect(() => {
    handleListTools();
  }, [handleListTools]);

  const handleExecuteTool = useCallback(async () => {
    if (!selectedTool) return;

    setExecutingTool(true);
    setError(null);
    setToolResult(null);

    try {
      console.log("Executing tool with arguments:", {
        toolName: selectedTool.name,
        arguments: toolArguments,
        argumentTypes: Object.fromEntries(
          Object.entries(toolArguments).map(([key, value]) => [
            key,
            typeof value,
          ])
        ),
      });

      const result = await mcpAPI.callTool(
        serverParams,
        selectedTool.name,
        toolArguments
      );

      if (result.status) {
        setToolResult(result.result || null);
      } else {
        setError(result.message);
      }
    } catch (err: any) {
      setError(`Failed to execute tool: ${err.message}`);
    } finally {
      setExecutingTool(false);
    }
  }, [serverParams, selectedTool, toolArguments]);

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
              onClick={handleListTools}
              icon={<Wrench size={16} />}
            >
              Load Tools
            </Button>
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
              onClick={handleListTools}
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
                {selectedTool.annotations?.readOnlyHint && (
                  <Tag color="green" className="text-xs">
                    Read-only
                  </Tag>
                )}
                {selectedTool.annotations?.destructiveHint && (
                  <Tag color="red" className="text-xs">
                    Destructive
                  </Tag>
                )}
                {selectedTool.annotations?.idempotentHint && (
                  <Tag color="purple" className="text-xs">
                    Idempotent
                  </Tag>
                )}
                {selectedTool.annotations?.openWorldHint && (
                  <Tag color="orange" className="text-xs">
                    Open-world
                  </Tag>
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
      <Card size="small" title={`Configure ${selectedTool.name}`}>
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
        title={
          <Space>
            <CheckCircle size={16} color="green" />
            Tool Result
          </Space>
        }
      >
        <div ref={toolResultRef}>
          <Space direction="vertical" style={{ width: "100%" }}>
            {toolResult.content.map((content, index) => (
              <Card
                key={index}
                size="small"
                style={{ backgroundColor: "#f9f9f9" }}
              >
                <Space direction="vertical" style={{ width: "100%" }}>
                  <Tag color="blue">{content.type}</Tag>
                  {content.text && (
                    <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
                      {content.text}
                    </pre>
                  )}
                  {content.data && (
                    <div>
                      <Text strong>Data:</Text>
                      <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
                        {content.data}
                      </pre>
                    </div>
                  )}
                  {content.mimeType && (
                    <Text type="secondary">MIME Type: {content.mimeType}</Text>
                  )}
                </Space>
              </Card>
            ))}
          </Space>
        </div>
      </Card>
    );
  };

  if (error) {
    return (
      <Alert
        type="error"
        message="Tools Error"
        description={error}
        action={
          <Button size="small" onClick={handleListTools} loading={loadingTools}>
            Retry
          </Button>
        }
      />
    );
  }

  return (
    <div style={{ width: "100%", maxWidth: "100%", overflow: "hidden" }}>
      <Space direction="vertical" style={{ width: "100%" }}>
        {renderToolSelector()}
        {selectedTool && !loadingTools && (
          <>
            <Divider />
            {renderArgumentsForm()}
          </>
        )}
        {toolResult && !loadingTools && (
          <>
            <Divider />
            {renderToolResult()}
          </>
        )}
      </Space>
    </div>
  );
};
