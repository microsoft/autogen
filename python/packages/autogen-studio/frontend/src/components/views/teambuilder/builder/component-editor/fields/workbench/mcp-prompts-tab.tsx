import React, { useState, useCallback, useEffect } from "react";
import {
  Button,
  Form,
  Input,
  Typography,
  Space,
  Alert,
  Card,
  List,
  Select,
  Tag,
  Divider,
} from "antd";
import { FileText, Eye, Play } from "lucide-react";
import { McpServerParams } from "../../../../../../types/datamodel";
import { mcpAPI } from "../../../../../mcp/api";

const { Text } = Typography;
const { TextArea } = Input;
const { Option } = Select;

interface Prompt {
  name: string;
  description?: string;
  arguments?: Array<{
    name: string;
    description?: string;
    required?: boolean;
  }>;
}

interface PromptMessage {
  role: "user" | "assistant";
  content: {
    type: "text";
    text: string;
  };
}

interface PromptResult {
  name: string;
  description?: string;
  messages: PromptMessage[];
}

interface McpPromptsTabProps {
  serverParams: McpServerParams;
}

export const McpPromptsTab: React.FC<McpPromptsTabProps> = ({
  serverParams,
}) => {
  const [prompts, setPrompts] = useState<Prompt[]>([]);
  const [selectedPrompt, setSelectedPrompt] = useState<Prompt | null>(null);
  const [promptArguments, setPromptArguments] = useState<Record<string, any>>(
    {}
  );
  const [promptResult, setPromptResult] = useState<PromptResult | null>(null);
  const [loadingPrompts, setLoadingPrompts] = useState(false);
  const [loadingPrompt, setLoadingPrompt] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleListPrompts = useCallback(async () => {
    setLoadingPrompts(true);
    setError(null);

    try {
      const result = await mcpAPI.listPrompts(serverParams);

      if (result.status) {
        setPrompts(result.prompts || []);
      } else {
        setError(result.message);
      }
    } catch (err: any) {
      setError(`Failed to fetch prompts: ${err.message}`);
    } finally {
      setLoadingPrompts(false);
    }
  }, [serverParams]);

  const handleGetPrompt = useCallback(
    async (prompt: Prompt) => {
      setLoadingPrompt(true);
      setError(null);
      setSelectedPrompt(prompt);

      try {
        const result = await mcpAPI.getPrompt(
          serverParams,
          prompt.name,
          promptArguments
        );

        if (result.status) {
          setPromptResult({
            name: result.name || prompt.name,
            description: result.description,
            messages: result.messages || [],
          });
        } else {
          setError(result.message);
        }
      } catch (err: any) {
        setError(`Failed to get prompt: ${err.message}`);
      } finally {
        setLoadingPrompt(false);
      }
    },
    [serverParams, promptArguments]
  );

  // Load prompts on mount
  useEffect(() => {
    handleListPrompts();
  }, [handleListPrompts]);

  // Auto-select first prompt when prompts are loaded
  useEffect(() => {
    if (prompts.length > 0 && !selectedPrompt) {
      setSelectedPrompt(prompts[0]);
      setPromptArguments({});
      setPromptResult(null);
    }
  }, [prompts, selectedPrompt]);

  const renderPromptsList = () => (
    <Card size="small" title="Available Prompts">
      <Space direction="vertical" style={{ width: "100%" }}>
        <Button
          type="primary"
          onClick={handleListPrompts}
          loading={loadingPrompts}
          icon={<FileText size={16} />}
        >
          {prompts.length > 0 ? "Refresh Prompts" : "Load Prompts"}
        </Button>

        {prompts.length > 0 && (
          <Select
            style={{ width: "100%" }}
            placeholder="Select a prompt to view"
            value={selectedPrompt?.name}
            onChange={(promptName) => {
              const prompt = prompts.find((p) => p.name === promptName);
              setSelectedPrompt(prompt || null);
              setPromptArguments({});
              setPromptResult(null);
            }}
          >
            {prompts.map((prompt) => (
              <Option
                key={prompt.name}
                value={prompt.name}
                title={prompt.description}
              >
                <Text strong>{prompt.name}</Text>
              </Option>
            ))}
          </Select>
        )}

        {prompts.length > 0 && (
          <Text type="secondary">Found {prompts.length} prompt(s)</Text>
        )}
      </Space>
    </Card>
  );

  const renderPromptForm = () => {
    if (!selectedPrompt) return null;

    const promptArgs = selectedPrompt.arguments || [];

    return (
      <Card size="small" title={`Configure ${selectedPrompt.name}`}>
        <Space direction="vertical" style={{ width: "100%" }}>
          {selectedPrompt.description && (
            <Text type="secondary">{selectedPrompt.description}</Text>
          )}

          {promptArgs.length > 0 ? (
            <Form layout="vertical">
              {promptArgs.map((arg) => (
                <Form.Item
                  key={arg.name}
                  label={
                    <Space>
                      <Text>{arg.name}</Text>
                      {arg.required && <Tag color="red">Required</Tag>}
                    </Space>
                  }
                >
                  <Input
                    placeholder={arg.description || `Enter ${arg.name}`}
                    value={promptArguments[arg.name] || ""}
                    onChange={(e) =>
                      setPromptArguments({
                        ...promptArguments,
                        [arg.name]: e.target.value,
                      })
                    }
                  />
                  {arg.description && (
                    <Text type="secondary" style={{ fontSize: "12px" }}>
                      {arg.description}
                    </Text>
                  )}
                </Form.Item>
              ))}
            </Form>
          ) : (
            <Text type="secondary">This prompt has no arguments</Text>
          )}

          <Button
            type="primary"
            icon={<Play size={16} />}
            onClick={() => handleGetPrompt(selectedPrompt)}
            loading={loadingPrompt}
            style={{ width: "100%" }}
          >
            {loadingPrompt ? "Loading..." : "Get Prompt"}
          </Button>
        </Space>
      </Card>
    );
  };

  const renderPromptResult = () => {
    if (!promptResult) return null;

    return (
      <Card
        size="small"
        title={
          <Space>
            <Eye size={16} />
            Prompt: {promptResult.name}
          </Space>
        }
      >
        <Space direction="vertical" style={{ width: "100%" }}>
          {promptResult.description && (
            <Text type="secondary">{promptResult.description}</Text>
          )}

          {promptResult.messages.map((message, index) => (
            <Card
              key={index}
              size="small"
              style={{
                backgroundColor:
                  message.role === "user" ? "#f0f8ff" : "#f9f9f9",
                borderLeft: `4px solid ${
                  message.role === "user" ? "#1890ff" : "#52c41a"
                }`,
              }}
            >
              <Space direction="vertical" style={{ width: "100%" }}>
                <Space>
                  <Tag color={message.role === "user" ? "blue" : "green"}>
                    {message.role}
                  </Tag>
                  <Tag color="gray">{message.content.type}</Tag>
                </Space>

                <div
                  style={{
                    whiteSpace: "pre-wrap",
                    fontFamily: "monospace",
                    fontSize: "13px",
                    lineHeight: "1.4",
                  }}
                >
                  {message.content.text}
                </div>
              </Space>
            </Card>
          ))}

          {promptResult.messages.length === 0 && (
            <Text type="secondary">No messages in this prompt</Text>
          )}
        </Space>
      </Card>
    );
  };

  if (error) {
    return (
      <Alert
        type="error"
        message="Prompts Error"
        description={error}
        action={
          <Button
            size="small"
            onClick={handleListPrompts}
            loading={loadingPrompts}
          >
            Retry
          </Button>
        }
      />
    );
  }

  return (
    <Space direction="vertical" style={{ width: "100%" }}>
      {renderPromptsList()}
      {selectedPrompt && (
        <>
          <Divider />
          {renderPromptForm()}
        </>
      )}
      {promptResult && (
        <>
          <Divider />
          {renderPromptResult()}
        </>
      )}
    </Space>
  );
};
