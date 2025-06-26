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
} from "antd";
import { PlayCircle, Wrench, CheckCircle, XCircle } from "lucide-react";
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
          Object.entries(toolArguments).map(([key, value]) => [key, typeof value])
        )
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

  const renderToolSelector = () => (
    <Card size="small" title="Available Tools">
      <Space direction="vertical" style={{ width: "100%" }}>
        <Button
          type="primary"
          onClick={handleListTools}
          loading={loadingTools}
          icon={<Wrench size={16} />}
        >
          {tools.length > 0 ? "Refresh Tools" : "Load Tools"}
        </Button>

        {tools.length > 0 && (
          <Select
            style={{ width: "100%" }}
            placeholder="Select a tool to test"
            value={selectedTool?.name}
            onChange={(toolName) => {
              const tool = tools.find((t) => t.name === toolName);
              setSelectedTool(tool || null);
              setToolResult(null);
              
              // Initialize tool arguments with default values based on schema
              const initialArgs: Record<string, any> = {};
              if (tool) {
                const schema = tool.inputSchema;
                const properties = schema?.properties || {};
                
                Object.entries(properties).forEach(([key, propSchema]: [string, any]) => {
                  if (propSchema.default !== undefined) {
                    initialArgs[key] = propSchema.default;
                  }
                });
              }
              
              setToolArguments(initialArgs);
            }}
          >
            {tools.map((tool) => (
              <Option
                key={tool.name}
                value={tool.name}
                title={tool.description}
              >
                <Text strong>{tool.name}</Text>
              </Option>
            ))}
          </Select>
        )}

        {tools.length > 0 && (
          <Text type="secondary">Found {tools.length} tool(s)</Text>
        )}
      </Space>
    </Card>
  );

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
                      type={propSchema.type === "number" || propSchema.type === "integer" ? "number" : "text"}
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
                  {(propSchema.type === "integer" || propSchema.type === "number") && (
                    <Text type="secondary" style={{ fontSize: "11px", fontStyle: "italic" }}>
                      Expected: {propSchema.type} | Current: {typeof toolArguments[key]} | Value: {JSON.stringify(toolArguments[key])}
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
    <Space direction="vertical" style={{ width: "100%" }}>
      {renderToolSelector()}
      {selectedTool && (
        <>
          <Divider />
          {renderArgumentsForm()}
        </>
      )}
      {toolResult && (
        <>
          <Divider />
          {renderToolResult()}
        </>
      )}
    </Space>
  );
};
