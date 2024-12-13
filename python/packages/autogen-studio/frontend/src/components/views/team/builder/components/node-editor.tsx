import React, { useEffect, useState } from "react";
import { Drawer, Button, Space, message, Select, Input } from "antd";
import { NodeEditorProps } from "../types";
import { useTeamBuilderStore } from "../store";
import {
  TeamConfigTypes,
  ComponentTypes,
  TeamTypes,
  ModelTypes,
  SelectorGroupChatConfig,
  RoundRobinGroupChatConfig,
  ModelConfigTypes,
  AzureOpenAIModelConfig,
  OpenAIModelConfig,
  ComponentConfigTypes,
  AgentConfig,
  ToolConfig,
  AgentTypes,
  ToolTypes,
  TerminationConfigTypes,
  TerminationTypes,
  MaxMessageTerminationConfig,
  TextMentionTerminationConfig,
  CombinationTerminationConfig,
} from "../../../../types/datamodel";

const { TextArea } = Input;

interface EditorProps<T> {
  value: T;
  onChange: (value: T) => void;
  disabled?: boolean;
}

const TeamEditor: React.FC<EditorProps<TeamConfigTypes>> = ({
  value,
  onChange,
  disabled,
}) => {
  const handleTypeChange = (teamType: TeamTypes) => {
    if (teamType === "SelectorGroupChat") {
      onChange({
        ...value,
        team_type: teamType,
        selector_prompt: "",
        model_client: {
          component_type: "model",
          model: "",
          model_type: "OpenAIChatCompletionClient",
        },
      } as SelectorGroupChatConfig);
    } else {
      const { selector_prompt, model_client, ...rest } =
        value as SelectorGroupChatConfig;
      onChange({
        ...rest,
        team_type: teamType,
      } as RoundRobinGroupChatConfig);
    }
  };

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <div>
        <label className="block text-sm font-medium mb-2">Team Type</label>
        <Select
          value={value.team_type}
          onChange={handleTypeChange}
          disabled={disabled}
          style={{ width: "100%" }}
          options={[
            { value: "RoundRobinGroupChat", label: "Round Robin" },
            { value: "SelectorGroupChat", label: "Selector" },
          ]}
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Name</label>
        <Input
          value={value.name}
          onChange={(e) => onChange({ ...value, name: e.target.value })}
          disabled={disabled}
        />
      </div>

      {value.team_type === "SelectorGroupChat" && (
        <>
          <div>
            <label className="block text-sm font-medium mb-2">
              Selector Prompt
            </label>
            <TextArea
              value={(value as SelectorGroupChatConfig).selector_prompt}
              onChange={(e) =>
                onChange({
                  ...value,
                  selector_prompt: e.target.value,
                } as SelectorGroupChatConfig)
              }
              disabled={disabled}
              rows={4}
            />
          </div>

          <ModelEditor
            value={(value as SelectorGroupChatConfig).model_client}
            onChange={(modelConfig) =>
              onChange({
                ...value,
                model_client: modelConfig,
              } as SelectorGroupChatConfig)
            }
            disabled={disabled}
          />
        </>
      )}
    </Space>
  );
};

const ModelEditor: React.FC<EditorProps<ModelConfigTypes>> = ({
  value,
  onChange,
  disabled,
}) => {
  const handleTypeChange = (modelType: ModelTypes) => {
    if (modelType === "AzureOpenAIChatCompletionClient") {
      onChange({
        ...value,
        model_type: modelType,
        azure_deployment: "",
        api_version: "",
        azure_endpoint: "",
        azure_ad_token_provider: "",
      } as AzureOpenAIModelConfig);
    } else {
      const {
        azure_deployment,
        api_version,
        azure_endpoint,
        azure_ad_token_provider,
        ...rest
      } = value as AzureOpenAIModelConfig;
      onChange({
        ...rest,
        model_type: modelType,
      } as OpenAIModelConfig);
    }
  };

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <div>
        <label className="block text-sm font-medium mb-2">Model Type</label>
        <Select
          value={value.model_type}
          onChange={handleTypeChange}
          disabled={disabled}
          style={{ width: "100%" }}
          options={[
            { value: "OpenAIChatCompletionClient", label: "OpenAI" },
            { value: "AzureOpenAIChatCompletionClient", label: "Azure OpenAI" },
          ]}
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Model</label>
        <Input
          value={value.model}
          onChange={(e) => onChange({ ...value, model: e.target.value })}
          disabled={disabled}
        />
      </div>

      {value.model_type === "OpenAIChatCompletionClient" && (
        <div>
          <label className="block text-sm font-medium mb-2">API Key</label>
          <Input.Password
            value={(value as OpenAIModelConfig).api_key}
            onChange={(e) =>
              onChange({
                ...value,
                api_key: e.target.value,
              } as OpenAIModelConfig)
            }
            disabled={disabled}
          />
        </div>
      )}

      {value.model_type === "AzureOpenAIChatCompletionClient" && (
        <Space direction="vertical" size="middle" style={{ width: "100%" }}>
          <div>
            <label className="block text-sm font-medium mb-2">
              Azure Deployment
            </label>
            <Input
              value={(value as AzureOpenAIModelConfig).azure_deployment}
              onChange={(e) =>
                onChange({
                  ...value,
                  azure_deployment: e.target.value,
                } as AzureOpenAIModelConfig)
              }
              disabled={disabled}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              API Version
            </label>
            <Input
              value={(value as AzureOpenAIModelConfig).api_version}
              onChange={(e) =>
                onChange({
                  ...value,
                  api_version: e.target.value,
                } as AzureOpenAIModelConfig)
              }
              disabled={disabled}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              Azure Endpoint
            </label>
            <Input
              value={(value as AzureOpenAIModelConfig).azure_endpoint}
              onChange={(e) =>
                onChange({
                  ...value,
                  azure_endpoint: e.target.value,
                } as AzureOpenAIModelConfig)
              }
              disabled={disabled}
            />
          </div>
        </Space>
      )}
    </Space>
  );
};

const AgentEditor: React.FC<EditorProps<AgentConfig>> = ({
  value,
  onChange,
  disabled,
}) => {
  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <div>
        <label className="block text-sm font-medium mb-2">Agent Type</label>
        <Select
          value={value.agent_type}
          onChange={(type: AgentTypes) =>
            onChange({ ...value, agent_type: type })
          }
          disabled={disabled}
          style={{ width: "100%" }}
          options={[
            { value: "AssistantAgent", label: "Assistant Agent" },
            { value: "CodingAssistantAgent", label: "Coding Assistant" },
            { value: "UserProxyAgent", label: "User Proxy" },
            { value: "MultimodalWebSurfer", label: "Web Surfer" },
            { value: "FileSurfer", label: "File Surfer" },
            { value: "MagenticOneCoderAgent", label: "Magnetic One Coder" },
          ]}
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Name</label>
        <Input
          value={value.name}
          onChange={(e) => onChange({ ...value, name: e.target.value })}
          disabled={disabled}
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">System Message</label>
        <TextArea
          value={value.system_message}
          onChange={(e) =>
            onChange({ ...value, system_message: e.target.value })
          }
          disabled={disabled}
          rows={4}
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Description</label>
        <TextArea
          value={value.description}
          onChange={(e) => onChange({ ...value, description: e.target.value })}
          disabled={disabled}
          rows={2}
        />
      </div>
    </Space>
  );
};

const ToolEditor: React.FC<EditorProps<ToolConfig>> = ({
  value,
  onChange,
  disabled,
}) => {
  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <div>
        <label className="block text-sm font-medium mb-2">Tool Type</label>
        <Select
          value={value.tool_type}
          onChange={(type: ToolTypes) =>
            onChange({ ...value, tool_type: type })
          }
          disabled={disabled}
          style={{ width: "100%" }}
          options={[{ value: "PythonFunction", label: "Python Function" }]}
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Name</label>
        <Input
          value={value.name}
          onChange={(e) => onChange({ ...value, name: e.target.value })}
          disabled={disabled}
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Description</label>
        <TextArea
          value={value.description}
          onChange={(e) => onChange({ ...value, description: e.target.value })}
          disabled={disabled}
          rows={2}
        />
      </div>

      <div>
        <label className="block text-sm font-medium mb-2">Content</label>
        <TextArea
          value={value.content}
          onChange={(e) => onChange({ ...value, content: e.target.value })}
          disabled={disabled}
          rows={8}
        />
      </div>
    </Space>
  );
};

const TerminationEditor: React.FC<EditorProps<TerminationConfigTypes>> = ({
  value,
  onChange,
  disabled,
}) => {
  const handleTypeChange = (terminationType: TerminationTypes) => {
    if (terminationType === "MaxMessageTermination") {
      onChange({
        component_type: "termination",
        termination_type: terminationType,
        max_messages: 100,
      } as MaxMessageTerminationConfig);
    } else if (terminationType === "TextMentionTermination") {
      onChange({
        component_type: "termination",
        termination_type: terminationType,
        text: "",
      } as TextMentionTerminationConfig);
    } else if (terminationType === "CombinationTermination") {
      onChange({
        component_type: "termination",
        termination_type: terminationType,
        operator: "or",
        conditions: [],
      } as CombinationTerminationConfig);
    }
  };

  const handleOperatorChange = (operator: "and" | "or") => {
    if (value.termination_type === "CombinationTermination") {
      onChange({
        ...value,
        operator,
      } as CombinationTerminationConfig);
    }
  };

  const handleAddCondition = () => {
    if (value.termination_type === "CombinationTermination") {
      onChange({
        ...value,
        conditions: [
          ...value.conditions,
          {
            component_type: "termination",
            termination_type: "MaxMessageTermination",
            max_messages: 100,
          },
        ],
      } as CombinationTerminationConfig);
    }
  };

  const handleUpdateCondition = (
    index: number,
    newCondition: TerminationConfigTypes
  ) => {
    if (value.termination_type === "CombinationTermination") {
      const newConditions = [...value.conditions];
      newConditions[index] = newCondition;
      onChange({
        ...value,
        conditions: newConditions,
      } as CombinationTerminationConfig);
    }
  };

  const handleRemoveCondition = (index: number) => {
    if (value.termination_type === "CombinationTermination") {
      onChange({
        ...value,
        conditions: value.conditions.filter((_, i) => i !== index),
      } as CombinationTerminationConfig);
    }
  };

  return (
    <Space direction="vertical" size="large" style={{ width: "100%" }}>
      <div>
        <label className="block text-sm font-medium mb-2">
          Termination Type
        </label>
        <Select
          value={value.termination_type}
          onChange={handleTypeChange}
          disabled={disabled}
          style={{ width: "100%" }}
          options={[
            { value: "MaxMessageTermination", label: "Max Messages" },
            { value: "TextMentionTermination", label: "Text Mention" },
            { value: "CombinationTermination", label: "Combination" },
          ]}
        />
      </div>

      {value.termination_type === "MaxMessageTermination" && (
        <div>
          <label className="block text-sm font-medium mb-2">Max Messages</label>
          <Input
            type="number"
            value={(value as MaxMessageTerminationConfig).max_messages}
            onChange={(e) =>
              onChange({
                ...value,
                max_messages: parseInt(e.target.value),
              } as MaxMessageTerminationConfig)
            }
            disabled={disabled}
          />
        </div>
      )}

      {value.termination_type === "TextMentionTermination" && (
        <div>
          <label className="block text-sm font-medium mb-2">
            Text to Match
          </label>
          <Input
            value={(value as TextMentionTerminationConfig).text}
            onChange={(e) =>
              onChange({
                ...value,
                text: e.target.value,
              } as TextMentionTerminationConfig)
            }
            disabled={disabled}
          />
        </div>
      )}

      {value.termination_type === "CombinationTermination" && (
        <Space direction="vertical" size="middle" style={{ width: "100%" }}>
          <div>
            <label className="block text-sm font-medium mb-2">Operator</label>
            <Select
              value={(value as CombinationTerminationConfig).operator}
              onChange={handleOperatorChange}
              disabled={disabled}
              style={{ width: "100%" }}
              options={[
                { value: "and", label: "AND" },
                { value: "or", label: "OR" },
              ]}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">Conditions</label>
            <Space direction="vertical" size="middle" style={{ width: "100%" }}>
              {(value as CombinationTerminationConfig).conditions.map(
                (condition, index) => (
                  <div key={index} className="border p-4 rounded-md">
                    <Space
                      direction="vertical"
                      size="middle"
                      style={{ width: "100%" }}
                    >
                      <TerminationEditor
                        value={condition}
                        onChange={(newCondition) =>
                          handleUpdateCondition(index, newCondition)
                        }
                        disabled={disabled}
                      />
                      <Button
                        danger
                        onClick={() => handleRemoveCondition(index)}
                        disabled={disabled}
                      >
                        Remove Condition
                      </Button>
                    </Space>
                  </div>
                )
              )}
              <Button
                type="dashed"
                onClick={handleAddCondition}
                disabled={disabled}
                style={{ width: "100%" }}
              >
                Add Condition
              </Button>
            </Space>
          </div>
        </Space>
      )}
    </Space>
  );
};

// Component type to editor mapping
const EditorComponents: Record<ComponentTypes, React.FC<EditorProps<any>>> = {
  team: TeamEditor,
  model: ModelEditor,
  agent: AgentEditor,
  tool: ToolEditor,
  termination: TerminationEditor,
};

export const NodeEditor: React.FC<NodeEditorProps> = ({ node, onUpdate }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [config, setConfig] = useState<ComponentConfigTypes | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const setSelectedNode = useTeamBuilderStore((state) => state.setSelectedNode);
  const [messageApi, contextHolder] = message.useMessage();

  useEffect(() => {
    if (node) {
      setIsOpen(true);
      setConfig(node.data.config as ComponentConfigTypes);
    } else {
      setIsOpen(false);
    }
  }, [node]);

  const handleClose = () => {
    setSelectedNode(null);
  };

  const handleSave = async () => {
    try {
      setIsSaving(true);
      if (!config) throw new Error("No configuration to save");

      // Validate config based on its type
      validateConfig(config);

      onUpdate({ config });
      messageApi.success("Changes saved successfully");
      setSelectedNode(null);
    } catch (error) {
      console.error("Save failed:", error);
      messageApi.error(error instanceof Error ? error.message : "Save failed");
    } finally {
      setIsSaving(false);
    }
  };

  if (!node || !config) return null;

  const EditorComponent = EditorComponents[node.data.type];
  if (!EditorComponent) return null;

  return (
    <Drawer
      title={`Edit ${node.data.label}`}
      placement="right"
      width={500}
      open={isOpen}
      onClose={handleClose}
      extra={
        <Space>
          <Button onClick={handleClose}>Cancel</Button>
          <Button type="primary" onClick={handleSave} loading={isSaving}>
            Update
          </Button>
        </Space>
      }
    >
      {contextHolder}
      <EditorComponent
        value={config}
        onChange={setConfig}
        disabled={isSaving}
      />
    </Drawer>
  );
};

// Type-safe validation functions
function validateConfig(config: ComponentConfigTypes): void {
  switch (config.component_type) {
    case "team": {
      const teamConfig = config as TeamConfigTypes;
      if ("selector_prompt" in teamConfig) {
        // Type guard for SelectorGroupChatConfig
        if (!teamConfig.selector_prompt) {
          throw new Error("Selector prompt is required");
        }
        if (!teamConfig.model_client) {
          throw new Error("Model configuration is required for selector team");
        }
      }
      break;
    }

    case "model":
      const modelConfig = config as ModelConfigTypes;
      if ("AzureOpenAIChatCompletionClient" in modelConfig) {
        const azureConfig = config as AzureOpenAIModelConfig;
        if (
          !azureConfig.azure_deployment ||
          !azureConfig.api_version ||
          !azureConfig.azure_endpoint
        ) {
          throw new Error("Azure OpenAI configuration is incomplete");
        }
      }
      break;
    // Add other type-specific validations as needed
  }
}

export default NodeEditor;
