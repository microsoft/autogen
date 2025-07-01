import React, { useState, useCallback, useEffect, useRef } from "react";
import { Button, Form, Input, Typography, Space, Alert, Select } from "antd";
import {
  FileText,
  Eye,
  Play,
  RotateCcw,
  MessageCircle,
  User,
  Bot,
  Hash,
} from "lucide-react";
import { McpServerParams } from "../../../../../../types/datamodel";
import { McpWebSocketClient, ServerCapabilities } from "../../../../../mcp/api";

const { Text } = Typography;
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
  wsClient: McpWebSocketClient | null;
  connected: boolean;
  capabilities: ServerCapabilities | null;
}

export const McpPromptsTab: React.FC<McpPromptsTabProps> = ({
  serverParams,
  wsClient,
  connected,
  capabilities,
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
  const [loadingError, setLoadingError] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<
    Record<string, string>
  >({});
  const promptResultRef = useRef<HTMLDivElement>(null);

  const handleListPrompts = useCallback(async () => {
    if (!connected || !wsClient) {
      setLoadingError("WebSocket not connected");
      return;
    }

    setLoadingPrompts(true);
    setLoadingError(null);

    try {
      const result = await wsClient.executeOperation({
        operation: "list_prompts",
      });

      if (result?.prompts) {
        setPrompts(result.prompts);
      } else {
        setLoadingError("No prompts received from server");
      }
    } catch (err: any) {
      setLoadingError(
        `Failed to fetch prompts: ${err.message || "Unknown error"}`
      );
    } finally {
      setLoadingPrompts(false);
    }
  }, [connected, wsClient]);

  // Validation function for required prompt arguments
  const validatePromptArguments = useCallback(
    (prompt: Prompt, promptArgs: Record<string, any>): string[] => {
      const errors: string[] = [];
      const requiredArgs =
        prompt.arguments?.filter((arg) => arg.required) || [];

      requiredArgs.forEach((arg) => {
        const value = promptArgs[arg.name];

        // Check if required field is missing, empty, or only whitespace
        if (
          value === undefined ||
          value === null ||
          (typeof value === "string" && value.trim() === "")
        ) {
          errors.push(`Required argument '${arg.name}' is missing or empty`);
        }
      });

      return errors;
    },
    []
  );

  // Real-time validation function
  const validateField = useCallback(
    (fieldName: string, value: string, isRequired: boolean): string | null => {
      if (isRequired && (!value || value.trim() === "")) {
        return `${fieldName} is required`;
      }
      return null;
    },
    []
  );

  // Handle argument change with validation
  const handleArgumentChange = useCallback(
    (argName: string, value: string, isRequired: boolean) => {
      // Update the argument value
      setPromptArguments((prev) => ({
        ...prev,
        [argName]: value,
      }));

      // Validate the field
      const error = validateField(argName, value, isRequired);
      setValidationErrors((prev) => ({
        ...prev,
        [argName]: error || "",
      }));
    },
    [validateField]
  );

  const handleGetPrompt = useCallback(
    async (prompt: Prompt) => {
      if (!connected || !wsClient) return;

      // Validate prompt arguments
      const validationErrors = validatePromptArguments(prompt, promptArguments);
      if (validationErrors.length > 0) {
        setError(validationErrors.join(", "));
        return;
      }

      setLoadingPrompt(true);
      setError(null);
      setSelectedPrompt(prompt);

      try {
        const result = await wsClient.executeOperation({
          operation: "get_prompt",
          name: prompt.name,
          arguments: promptArguments,
        });

        if (result) {
          setPromptResult({
            name: result.name || prompt.name,
            description: result.description,
            messages: result.messages || [],
          });
        } else {
          setError("No prompt result received");
        }
      } catch (err: any) {
        setError(`Failed to get prompt: ${err.message || "Unknown error"}`);
      } finally {
        setLoadingPrompt(false);
      }
    },
    [connected, wsClient, promptArguments, validatePromptArguments]
  );

  // Auto-scroll to prompt result when it appears
  useEffect(() => {
    if (promptResult && promptResultRef.current) {
      setTimeout(() => {
        promptResultRef.current?.scrollIntoView({
          behavior: "smooth",
          block: "nearest",
        });
      }, 100);
    }
  }, [promptResult]);

  // Load prompts when connected and capabilities indicate prompts are available
  useEffect(() => {
    if (connected && capabilities?.prompts) {
      handleListPrompts();
    }
  }, [connected, capabilities?.prompts, handleListPrompts]);

  // Auto-select first prompt when prompts are loaded
  useEffect(() => {
    if (prompts.length > 0 && !selectedPrompt) {
      setSelectedPrompt(prompts[0]);
      setPromptArguments({});
      setPromptResult(null);
      setValidationErrors({});
    }
  }, [prompts, selectedPrompt]);

  const renderPromptsList = () => (
    <div className="bg-secondary rounded-lg border border-tertiary p-4">
      <div className="flex items-center gap-2 mb-4">
        <FileText size={18} className="text-primary" />
        <h3 className="text-lg font-semibold text-primary m-0">
          Available Prompts
        </h3>
      </div>

      <div className="space-y-4">
        <Button
          type="primary"
          onClick={handleListPrompts}
          loading={loadingPrompts}
          icon={<FileText size={16} />}
          className="flex items-center gap-2"
        >
          {prompts.length > 0 ? "Refresh Prompts" : "Load Prompts"}
        </Button>

        {loadingError && (
          <Alert
            type="error"
            message="Failed to Load Prompts"
            description={loadingError}
            action={
              <Space>
                <Button
                  size="small"
                  onClick={handleListPrompts}
                  loading={loadingPrompts}
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

        {prompts.length > 0 && (
          <div className="space-y-2">
            <Select
              className="w-full"
              placeholder="Select a prompt to view"
              value={selectedPrompt?.name}
              onChange={(promptName) => {
                const prompt = prompts.find((p) => p.name === promptName);
                setSelectedPrompt(prompt || null);
                setPromptArguments({});
                setPromptResult(null);
                setValidationErrors({});
                // Clear errors when selecting a new prompt to allow fresh attempts
                setError(null);
              }}
            >
              {prompts.map((prompt) => (
                <Option
                  key={prompt.name}
                  value={prompt.name}
                  title={prompt.description}
                >
                  <Text className="font-medium">{prompt.name}</Text>
                </Option>
              ))}
            </Select>

            <Text className="text-secondary text-sm">
              Found {prompts.length} prompt(s)
            </Text>
          </div>
        )}

        {prompts.length === 0 && !loadingPrompts && (
          <Text className="text-secondary text-center block py-4">
            No prompts found
          </Text>
        )}
      </div>
    </div>
  );

  const renderPromptForm = () => {
    if (!selectedPrompt) return null;

    const promptArgs = selectedPrompt.arguments || [];

    return (
      <div className="bg-secondary rounded-lg border border-tertiary p-4">
        <div className="flex items-center gap-2 mb-4">
          <MessageCircle size={18} className="text-primary" />
          <h3 className="text-lg font-semibold text-primary m-0">
            Configure {selectedPrompt.name}
          </h3>
        </div>

        <div className="space-y-4">
          {selectedPrompt.description && (
            <Text className="text-secondary block">
              {selectedPrompt.description}
            </Text>
          )}

          {promptArgs.length > 0 ? (
            <Form layout="vertical" className="space-y-4">
              {promptArgs.map((arg) => (
                <Form.Item
                  key={arg.name}
                  label={
                    <div className="flex items-center gap-2">
                      <Text className="font-medium text-primary">
                        {arg.name}
                      </Text>
                      {arg.required && (
                        <span className="inline-flex items-center px-2 py-1 text-xs font-medium bg-red-100 text-red-800 rounded-full">
                          Required
                        </span>
                      )}
                    </div>
                  }
                  className="mb-4"
                >
                  <Input
                    placeholder={arg.description || `Enter ${arg.name}`}
                    value={promptArguments[arg.name] || ""}
                    onChange={(e) =>
                      handleArgumentChange(
                        arg.name,
                        e.target.value,
                        arg.required || false
                      )
                    }
                    className="w-full"
                    status={validationErrors[arg.name] ? "error" : undefined}
                  />
                  {validationErrors[arg.name] && (
                    <Text className="text-red-500 text-xs mt-1 block">
                      {validationErrors[arg.name]}
                    </Text>
                  )}
                  {arg.description && (
                    <Text className="text-secondary text-xs mt-1 block">
                      {arg.description}
                    </Text>
                  )}
                </Form.Item>
              ))}
            </Form>
          ) : (
            <Text className="text-secondary">This prompt has no arguments</Text>
          )}

          <Button
            type="primary"
            icon={<Play size={16} />}
            onClick={() => handleGetPrompt(selectedPrompt)}
            loading={loadingPrompt}
            className="w-full flex items-center justify-center gap-2"
          >
            {loadingPrompt ? "Loading..." : "Get Prompt"}
          </Button>
        </div>
      </div>
    );
  };

  const renderPromptResult = () => {
    if (!promptResult) return null;

    return (
      <div
        ref={promptResultRef}
        className="bg-secondary rounded-lg border border-tertiary p-4"
      >
        <div className="flex items-center gap-2 mb-4">
          <Eye size={18} className="text-primary" />
          <h3 className="text-lg font-semibold text-primary m-0">
            Prompt: {promptResult.name}
          </h3>
        </div>

        <div className="space-y-4">
          {promptResult.description && (
            <Text className="text-secondary block">
              {promptResult.description}
            </Text>
          )}

          {promptResult.messages.length > 0 ? (
            <div className="space-y-3">
              {promptResult.messages.map((message, index) => (
                <div
                  key={index}
                  className={`rounded-lg border-l-4 p-4  bg-tertiary`}
                >
                  <div className="flex items-center gap-2 mb-2">
                    {message.role === "user" ? (
                      <User size={16} className="text-blue-600" />
                    ) : (
                      <Bot size={16} className="text-green-600" />
                    )}
                    <span
                      className={`inline-flex items-center px-2.5 py-1 text-sm font-medium rounded-full ${
                        message.role === "user"
                          ? "bg-blue-100 text-blue-800"
                          : "bg-green-100 text-green-800"
                      }`}
                    >
                      {message.role}
                    </span>
                    <span className="inline-flex items-center px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded-full">
                      {message.content.type}
                    </span>
                  </div>

                  <pre className="whitespace-pre-wrap font-mono text-sm text-primary leading-relaxed">
                    {message.content.text}
                  </pre>
                </div>
              ))}
            </div>
          ) : (
            <Text className="text-secondary text-center block py-4">
              No messages in this prompt
            </Text>
          )}
        </div>
      </div>
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
            icon={<RotateCcw size={14} />}
            className="flex items-center gap-1"
          >
            Retry
          </Button>
        }
        className="m-4"
      />
    );
  }

  return (
    <div className="mt-4 space-y-6 h-full overflow-auto">
      {renderPromptsList()}{" "}
      {selectedPrompt && !loadingError && (
        <>
          <div className="border-t border-tertiary" />
          {renderPromptForm()}
        </>
      )}
      {error && (
        <Alert
          type="error"
          message="Prompt Operation Error"
          description={error}
          action={
            <Space>
              <Button size="small" onClick={() => setError(null)}>
                Clear Error
              </Button>
              {selectedPrompt && (
                <Button
                  size="small"
                  type="primary"
                  onClick={() => handleGetPrompt(selectedPrompt)}
                  loading={loadingPrompt}
                >
                  Retry
                </Button>
              )}
            </Space>
          }
          showIcon
        />
      )}
      {promptResult && !loadingError && (
        <>
          <div className="border-t border-tertiary" />
          {renderPromptResult()}
        </>
      )}
    </div>
  );
};
