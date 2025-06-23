import React, { useState, useCallback, useEffect, useRef } from "react";
import {
  Button,
  Card,
  Form,
  Input,
  Typography,
  Space,
  Alert,
  Tag,
  Spin,
} from "antd";
import { PlayCircle, Wrench, CheckCircle, XCircle } from "lucide-react";
import { McpServerParams } from "../../../../../types/datamodel";
import { mcpAPI, McpTool, McpToolResult } from "../../../api";

const { TextArea } = Input;
const { Text } = Typography;

interface McpTestingPanelProps {
  serverParams: McpServerParams;
}

export const McpTestingPanel: React.FC<McpTestingPanelProps> = ({
  serverParams,
}) => {
  const [tools, setTools] = useState<McpTool[]>([]);
  const [selectedTool, setSelectedTool] = useState<McpTool | null>(null);
  const [toolArguments, setToolArguments] = useState<Record<string, any>>({});
  const [loadingTools, setLoadingTools] = useState(false);
  const [executingTool, setExecutingTool] = useState(false);
  const [toolResult, setToolResult] = useState<McpToolResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const runToolRef = useRef<HTMLDivElement>(null);
  const toolResultRef = useRef<HTMLDivElement>(null);

  // Auto-select first tool when tools are loaded
  useEffect(() => {
    if (tools.length > 0 && !selectedTool) {
      setSelectedTool(tools[0]);
      setToolArguments({});
      setToolResult(null);
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

  const handleExecuteTool = useCallback(async () => {
    if (!selectedTool) return;

    setExecutingTool(true);
    setError(null);
    setToolResult(null);

    try {
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
  }, [selectedTool, toolArguments, serverParams]);

  const handleToolSelect = (tool: McpTool) => {
    setSelectedTool(tool);
    setToolArguments({});
    setToolResult(null);
  };

  const renderArgumentForm = useCallback(() => {
    if (!selectedTool) return null;

    const { parameters } = selectedTool;
    const properties = parameters.properties || {};
    const required = parameters.required || [];

    return (
      <Form layout="vertical">
        {Object.entries(properties).map(([key, prop]: [string, any]) => (
          <Form.Item
            key={key}
            label={
              <span>
                {key}
                {required.includes(key) && (
                  <span style={{ color: "red" }}> *</span>
                )}
              </span>
            }
            help={prop.description}
          >
            {prop.type === "object" || prop.type === "array" ? (
              <TextArea
                placeholder={`Enter ${key} as JSON`}
                value={
                  toolArguments[key]
                    ? JSON.stringify(toolArguments[key], null, 2)
                    : ""
                }
                onChange={(e) => {
                  try {
                    const parsed = e.target.value
                      ? JSON.parse(e.target.value)
                      : undefined;
                    setToolArguments((prev) => ({
                      ...prev,
                      [key]: parsed,
                    }));
                  } catch {
                    // Invalid JSON, keep the string value for now
                    setToolArguments((prev) => ({
                      ...prev,
                      [key]: e.target.value,
                    }));
                  }
                }}
                rows={3}
              />
            ) : (
              <Input
                placeholder={`Enter ${key}`}
                value={toolArguments[key] || ""}
                onChange={(e) =>
                  setToolArguments((prev) => ({
                    ...prev,
                    [key]: e.target.value,
                  }))
                }
              />
            )}
          </Form.Item>
        ))}
      </Form>
    );
  }, [selectedTool, toolArguments]);

  const renderToolResult = useCallback(() => {
    if (!toolResult) return null;

    return (
      <div ref={toolResultRef}>
        <Card
          title={
            <Space>
              {toolResult.is_error ? (
                <XCircle className="w-4 h-4 text-red-500" />
              ) : (
                <CheckCircle className="w-4 h-4 text-green-500" />
              )}
              <span>Tool Result</span>
            </Space>
          }
          size="small"
          className="mt-4"
        >
          <pre className="whitespace-pre-wrap text-sm bg-secondary/30 p-3 rounded border max-h-96 overflow-y-auto">
            {toolResult.result.map((r, i) => r.content).join("\n")}
          </pre>
        </Card>
      </div>
    );
  }, [toolResult]);

  return (
    <Space direction="vertical" className="w-full">
      {/* List Tools Button - Always Visible */}
      <Space>
        <Button
          type="primary"
          onClick={handleListTools}
          loading={loadingTools}
          icon={<Wrench className="w-4 h-4" />}
        >
          List Available Tools
        </Button>
        {tools.length > 0 && (
          <Tag color="green">{tools.length} tools found</Tag>
        )}
      </Space>

      {/* Tools Pills */}
      {tools.length > 0 && (
        <div className="space-y-3">
          <div className="flex flex-wrap gap-2">
            {tools.map((tool) => (
              <Tag
                key={tool.name}
                className={`cursor-pointer px-3 py-1 border-2 transition-all ${
                  selectedTool?.name === tool.name
                    ? "border-blue-500 bg-blue-50 text-blue-700"
                    : "border-gray-200 hover:border-blue-300 hover:bg-blue-25"
                }`}
                onClick={() => handleToolSelect(tool)}
              >
                {tool.name}
              </Tag>
            ))}
          </div>

          {/* Selected Tool Details */}
          {selectedTool && (
            <Card size="small" className="mt-4">
              <Space direction="vertical" className="w-full">
                <div>
                  <Typography.Title level={5} className="mb-2">
                    {selectedTool.name}
                  </Typography.Title>
                  <Typography.Text type="secondary">
                    {selectedTool.description}
                  </Typography.Text>
                </div>

                {/* Arguments Form */}
                {renderArgumentForm()}

                {/* Run Tool Button */}
                <div ref={runToolRef}>
                  <Button
                    type="primary"
                    onClick={handleExecuteTool}
                    loading={executingTool}
                    icon={<PlayCircle className="w-4 h-4" />}
                    size="large"
                    className="w-full"
                  >
                    Run Tool
                  </Button>
                </div>

                {/* Tool Result */}
                {renderToolResult()}
              </Space>
            </Card>
          )}
        </div>
      )}

      {/* Error Display */}
      {error && (
        <Alert
          message="Error"
          description={error}
          type="error"
          showIcon
          closable
          onClose={() => setError(null)}
        />
      )}
    </Space>
  );
};

export default React.memo(McpTestingPanel);
