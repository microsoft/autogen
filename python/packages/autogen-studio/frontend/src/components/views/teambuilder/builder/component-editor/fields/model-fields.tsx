import React, { useCallback } from "react";
import { Input, InputNumber, Select, Tooltip, Collapse, Switch, AutoComplete } from "antd";
import TextArea from "antd/es/input/TextArea";
import { HelpCircle, Settings, User, Wrench } from "lucide-react";
import {
  Component,
  ComponentConfig,
  ModelConfig,
} from "../../../../../types/datamodel";
import {
  isOpenAIModel,
  isAzureOpenAIModel,
  isAnthropicModel,
} from "../../../../../types/guards";

interface ModelFieldsProps {
  component: Component<ModelConfig>;
  onChange: (updates: Partial<Component<ComponentConfig>>) => void;
}

const InputWithTooltip: React.FC<{
  label: string;
  tooltip: string;
  children: React.ReactNode;
}> = ({ label, tooltip, children }) => (
  <div className="block">
    <div className="flex items-center gap-2 mb-1">
      <span className="text-sm font-medium text-primary">{label}</span>
      <Tooltip title={tooltip}>
        <HelpCircle className="w-4 h-4 text-secondary" />
      </Tooltip>
    </div>
    {children}
  </div>
);

// Define possible field names to ensure type safety
type FieldName =
  | "temperature"
  | "max_tokens"
  | "top_p"
  | "top_k"
  | "frequency_penalty"
  | "presence_penalty"
  | "stop"
  | "stop_sequences"
  | "model"
  | "api_key"
  | "organization"
  | "base_url"
  | "timeout"
  | "max_retries"
  | "azure_endpoint"
  | "azure_deployment"
  | "api_version"
  | "azure_ad_token"
  | "tools"
  | "tool_choice"
  | "metadata"
  | "model_info";

// Define the field specification type
interface FieldSpec {
  label: string;
  tooltip: string;
  component: React.ComponentType<any>;
  props: Record<string, any>;
  transform?: {
    fromConfig: (value: any) => any;
    toConfig: (value: any, origValue?: any) => any;
  };
}

const defaultModelInfo = {
  vision: false,
  function_calling: false,
  json_output: false,
  structured_output: false,
  family: "",
  multiple_system_messages: false,
};

const ModelInfoEditor: React.FC<{
  value: any;
  onChange: (value: any) => void;
}> = ({ value, onChange }) => {
  const modelInfo = value || defaultModelInfo;

  const updateField = (field: string, newValue: any) => {
    onChange({
      ...modelInfo,
      [field]: newValue,
    });
  };

  return (
    <div className="space-y-4 p-4 border rounded-lg">
      <div className="grid grid-cols-2 gap-4">
        <InputWithTooltip
          label="Vision Support"
          tooltip="Enable vision support (image input capability)."
        >
          <Switch
            checked={modelInfo.vision}
            onChange={(checked) => updateField("vision", checked)}
            className="w-16"
          />
        </InputWithTooltip>

        <InputWithTooltip
          label="Function Calling"
          tooltip="Enable function calling feature for external integrations."
        >
          <Switch
            checked={modelInfo.function_calling}
            onChange={(checked) => updateField("function_calling", checked)}
            className="w-16"
          />
        </InputWithTooltip>

        <InputWithTooltip
          label="JSON Output"
          tooltip="Enable JSON output mode (distinct from structured output)."
        >
          <Switch
            checked={modelInfo.json_output}
            onChange={(checked) => updateField("json_output", checked)}
            className="w-16"
          />
        </InputWithTooltip>

        <InputWithTooltip
          label="Structured Output"
          tooltip="Enable structured output mode (distinct from JSON output)."
        >
          <Switch
            checked={modelInfo.structured_output}
            onChange={(checked) => updateField("structured_output", checked)}
            className="w-16"
          />
        </InputWithTooltip>

        <InputWithTooltip
          label="Multiple System Messages"
          tooltip="Enable support for multiple, non-consecutive system messages."
        >
          <Switch
            checked={modelInfo.multiple_system_messages}
            onChange={(checked) => updateField("multiple_system_messages", checked)}
            className="w-16"
          />
        </InputWithTooltip>
      </div>

      <InputWithTooltip
        label="Model Family"
        tooltip="Model family should be one of the constants from ModelFamily or a string for unknown families."
      >
        <AutoComplete
          value={modelInfo.family}
          onChange={(value) => updateField("family", value)}
          className="w-full mt-1"
          placeholder="Select or enter model family"
          options={[
            { label: "GPT-4.1", value: "gpt-41" },
            { label: "GPT-4.5", value: "gpt-45" },
            { label: "GPT-4o", value: "gpt-4o" },
            { label: "GPT-4", value: "gpt-4" },
            { label: "GPT-3.5", value: "gpt-35" },
            { label: "o1", value: "o1" },
            { label: "o3", value: "o3" },
            { label: "o4", value: "o4" },
            { label: "r1", value: "r1" },
            
            { label: "Gemini 1.5 Flash", value: "gemini-1.5-flash" },
            { label: "Gemini 1.5 Pro", value: "gemini-1.5-pro" },
            { label: "Gemini 2.0 Flash", value: "gemini-2.0-flash" },
            { label: "Gemini 2.5 Pro", value: "gemini-2.5-pro" },
            { label: "Gemini 2.5 Flash", value: "gemini-2.5-flash" },
            
            { label: "Claude 3 Haiku", value: "claude-3-haiku" },
            { label: "Claude 3 Sonnet", value: "claude-3-sonnet" },
            { label: "Claude 3 Opus", value: "claude-3-opus" },
            { label: "Claude 3.5 Haiku", value: "claude-3-5-haiku" },
            { label: "Claude 3.5 Sonnet", value: "claude-3-5-sonnet" },
            { label: "Claude 3.7 Sonnet", value: "claude-3-7-sonnet" },
            { label: "Claude 4 Opus", value: "claude-4-opus" },
            { label: "Claude 4 Sonnet", value: "claude-4-sonnet" },
            
            { label: "Llama 3.3 8B", value: "llama-3.3-8b" },
            { label: "Llama 3.3 70B", value: "llama-3.3-70b" },
            { label: "Llama 4 Scout", value: "llama-4-scout" },
            { label: "Llama 4 Maverick", value: "llama-4-maverick" },
            
            { label: "Codestral", value: "codestral" },
            { label: "Open Codestral Mamba", value: "open-codestral-mamba" },
            { label: "Mistral", value: "mistral" },
            { label: "Ministral", value: "ministral" },
            { label: "Pixtral", value: "pixtral" },
            
            { label: "Unknown", value: "unknown" },
          ]}
          filterOption={(input, option) =>
            (option?.label ?? "").toLowerCase().includes(input.toLowerCase())
          }
          allowClear
        />
      </InputWithTooltip>
    </div>
  );
};

// Field specifications for each possible model parameters
const fieldSpecs: Record<FieldName, FieldSpec> = {
  // Common fields
  temperature: {
    label: "Temperature",
    tooltip:
      "Controls randomness in the model's output. Higher values make output more random, lower values make it more focused.",
    component: InputNumber,
    props: { min: 0, max: 2, step: 0.1, className: "w-full" },
  },
  max_tokens: {
    label: "Max Tokens",
    tooltip: "Maximum length of the model's output in tokens",
    component: InputNumber,
    props: { min: 1, className: "w-full" },
  },
  top_p: {
    label: "Top P",
    tooltip:
      "Controls diversity via nucleus sampling. Lower values make output more focused, higher values make it more diverse.",
    component: InputNumber,
    props: { min: 0, max: 1, step: 0.1, className: "w-full" },
  },
  top_k: {
    label: "Top K",
    tooltip:
      "Limits the next token selection to the K most likely tokens. Only used by some models.",
    component: InputNumber,
    props: { min: 0, className: "w-full" },
  },
  frequency_penalty: {
    label: "Frequency Penalty",
    tooltip:
      "Decreases the model's likelihood to repeat the same information. Values range from -2.0 to 2.0.",
    component: InputNumber,
    props: { min: -2, max: 2, step: 0.1, className: "w-full" },
  },
  presence_penalty: {
    label: "Presence Penalty",
    tooltip:
      "Increases the model's likelihood to talk about new topics. Values range from -2.0 to 2.0.",
    component: InputNumber,
    props: { min: -2, max: 2, step: 0.1, className: "w-full" },
  },
  stop: {
    label: "Stop Sequences",
    tooltip: "Sequences where the model will stop generating further tokens",
    component: Select,
    props: {
      mode: "tags",
      placeholder: "Enter stop sequences",
      className: "w-full",
    },
  },
  stop_sequences: {
    label: "Stop Sequences",
    tooltip: "Sequences where the model will stop generating further tokens",
    component: Select,
    props: {
      mode: "tags",
      placeholder: "Enter stop sequences",
      className: "w-full",
    },
  },
  model: {
    label: "Model",
    tooltip: "The name of the model to use",
    component: Input,
    props: { required: true },
  },

  // OpenAI specific
  api_key: {
    label: "API Key",
    tooltip: "Your API key",
    component: Input.Password,
    props: {},
  },
  organization: {
    label: "Organization",
    tooltip: "Optional: Your OpenAI organization ID",
    component: Input,
    props: {},
  },
  base_url: {
    label: "Base URL",
    tooltip: "Optional: Custom base URL for API requests",
    component: Input,
    props: {},
  },
  timeout: {
    label: "Timeout",
    tooltip: "Request timeout in seconds",
    component: InputNumber,
    props: { min: 1, className: "w-full" },
  },
  max_retries: {
    label: "Max Retries",
    tooltip: "Maximum number of retry attempts for failed requests",
    component: InputNumber,
    props: { min: 0, className: "w-full" },
  },

  // Azure OpenAI specific
  azure_endpoint: {
    label: "Azure Endpoint",
    tooltip: "Your Azure OpenAI service endpoint URL",
    component: Input,
    props: { required: true },
  },
  azure_deployment: {
    label: "Azure Deployment",
    tooltip: "The name of your Azure OpenAI model deployment",
    component: Input,
    props: {},
  },
  api_version: {
    label: "API Version",
    tooltip: "Azure OpenAI API version (e.g., 2023-05-15)",
    component: Input,
    props: { required: true },
  },
  azure_ad_token: {
    label: "Azure AD Token",
    tooltip: "Optional: Azure Active Directory token for authentication",
    component: Input.Password,
    props: {},
  },

  // Anthropic specific
  tools: {
    label: "Tools",
    tooltip: "JSON definition of tools the model can use",
    component: TextArea,
    props: { rows: 4, placeholder: "Enter tools JSON definition" },
    transform: {
      fromConfig: (value: any) => (value ? JSON.stringify(value, null, 2) : ""),
      toConfig: (value: string) => {
        try {
          return value ? JSON.parse(value) : null;
        } catch (e) {
          return value; // Keep as string if invalid JSON
        }
      },
    },
  },
  tool_choice: {
    label: "Tool Choice",
    tooltip:
      "Controls whether the model uses tools ('auto', 'any', 'none', or JSON object)",
    component: Select,
    props: {
      options: [
        { label: "Auto", value: "auto" },
        { label: "Any", value: "any" },
        { label: "None", value: "none" },
        { label: "Custom", value: "custom" },
      ],
      className: "w-full",
    },
    transform: {
      fromConfig: (value: any) => {
        if (typeof value === "object") return "custom";
        return value || "auto";
      },
      toConfig: (value: string, origValue: any) => {
        if (value !== "custom") return value;
        // If it was custom before, keep the original object
        return typeof origValue === "object" ? origValue : { type: "function" };
      },
    },
  },
  metadata: {
    label: "Metadata",
    tooltip: "Optional: Custom metadata to include with the request",
    component: TextArea,
    props: { rows: 2, placeholder: "Enter metadata as JSON" },
    transform: {
      fromConfig: (value: any) => (value ? JSON.stringify(value, null, 2) : ""),
      toConfig: (value: string) => {
        try {
          return value ? JSON.parse(value) : null;
        } catch (e) {
          return value; // Keep as string if invalid JSON
        }
      },
    },
  },
  model_info: {
    label: "Model Information",
    tooltip: "Model capabilities and features",
    component: ModelInfoEditor,
    props: {},
    transform: {
      fromConfig: (value: any) => 
        value ? { ...defaultModelInfo, ...value } : defaultModelInfo,
      toConfig: (value: any) => ({ ...defaultModelInfo, ...value }),
    },
  },
};

// Define provider field mapping type
type ProviderType = "openai" | "azure" | "anthropic";

interface ProviderFields {
  modelConfig: FieldName[];
  modelParams: FieldName[];
  modelInfo: FieldName[];
}

// Define which fields each provider uses
const providerFields: Record<ProviderType, ProviderFields> = {
  openai: {
    modelConfig: [
      "model",
      "api_key",
      "organization",
      "base_url",
      "timeout",
      "max_retries",
    ],
    modelParams: [
      "temperature",
      "max_tokens",
      "top_p",
      "frequency_penalty",
      "presence_penalty",
      "stop",
    ],
    modelInfo: ["model_info"],
  },
  azure: {
    modelConfig: [
      "model",
      "api_key",
      "azure_endpoint",
      "azure_deployment",
      "api_version",
      "azure_ad_token",
      "timeout",
      "max_retries",
    ],
    modelParams: [
      "temperature",
      "max_tokens",
      "top_p",
      "frequency_penalty",
      "presence_penalty",
      "stop",
    ],
    modelInfo: ["model_info"],
  },
  anthropic: {
    modelConfig: ["model", "api_key", "base_url", "timeout", "max_retries"],
    modelParams: [
      "temperature",
      "max_tokens",
      "top_p",
      "top_k",
      "stop_sequences",
      "tools",
      "tool_choice",
      "metadata",
    ],
    modelInfo: ["model_info"],
  },
};

export const ModelFields: React.FC<ModelFieldsProps> = ({
  component,
  onChange,
}) => {
  // Determine which provider we're dealing with
  let providerType: ProviderType | null = null;
  if (isOpenAIModel(component)) {
    providerType = "openai";
  } else if (isAzureOpenAIModel(component)) {
    providerType = "azure";
  } else if (isAnthropicModel(component)) {
    providerType = "anthropic";
  }

  // Return null if we don't recognize the provider
  if (!providerType) return null;

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
    (field: FieldName, value: unknown) => {
      // Check if this field has a transform function
      const spec = fieldSpecs[field];
      const transformedValue = spec.transform?.toConfig
        ? spec.transform.toConfig(value, (component.config as any)[field])
        : value;

      handleComponentUpdate({
        config: {
          ...component.config,
          [field]: transformedValue,
        },
      });
    },
    [component, handleComponentUpdate]
  );

  // Function to render a single field
  const renderField = (fieldName: FieldName) => {
    const spec = fieldSpecs[fieldName];
    if (!spec) return null;

    // Get the current value, applying any transformation
    const value = spec.transform?.fromConfig
      ? spec.transform.fromConfig((component.config as any)[fieldName])
      : (component.config as any)[fieldName];

    return (
      <InputWithTooltip
        key={fieldName}
        label={spec.label}
        tooltip={spec.tooltip}
      >
        <spec.component
          {...spec.props}
          value={value}
          onChange={(val: any) => {
            // For some components like Input, the value is in e.target.value
            const newValue = val && val.target ? val.target.value : val;
            handleConfigUpdate(fieldName, newValue);
          }}
        />
      </InputWithTooltip>
    );
  };

  // Function to render a group of fields
  const renderFieldGroup = (fields: FieldName[]) => {
    return (
      <div className="space-y-4">
        {fields.map((field) => renderField(field))}
      </div>
    );
  };

  return (
    <Collapse
      defaultActiveKey={["details", "configuration", "parameters", "model_info"]}
      className="border-0"
      expandIconPosition="end"
      items={[
        {
          key: "details",
          label: (
            <div className="flex items-center gap-2">
              <User className="w-4 h-4 text-blue-500" />
              <span className="font-medium">Component Details</span>
            </div>
          ),
          children: (
            <div className="space-y-4">
              <label className="block">
                <span className="text-sm font-medium text-primary">Name</span>
                <Input
                  value={component.label || ""}
                  onChange={(e) =>
                    handleComponentUpdate({ label: e.target.value })
                  }
                  placeholder="Model name"
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
                  placeholder="Model description"
                  rows={4}
                  className="mt-1"
                />
              </label>
            </div>
          ),
        },
        {
          key: "configuration",
          label: (
            <div className="flex items-center gap-2">
              <Settings className="w-4 h-4 text-green-500" />
              <span className="font-medium">
                {providerType === "azure"
                  ? "Azure Configuration"
                  : "Model Configuration"}
              </span>
            </div>
          ),
          children: renderFieldGroup(providerFields[providerType].modelConfig),
        },
        {
          key: "parameters",
          label: (
            <div className="flex items-center gap-2">
              <Wrench className="w-4 h-4 text-orange-500" />
              <span className="font-medium">Model Parameters</span>
            </div>
          ),
          children: renderFieldGroup(providerFields[providerType].modelParams),
        },
        {
          key: "model_info",
          label: (
            <div className="flex items-center gap-2">
              <HelpCircle className="w-4 h-4 text-purple-500" />
              <span className="font-medium">Model Information</span>
            </div>
          ),
          children: renderFieldGroup(providerFields[providerType].modelInfo),
        },
        // Only render tool configuration if it's an Anthropic model and has tools
        ...(providerType === "anthropic" &&
        (component.config as any).tool_choice === "custom"
          ? [
              {
                key: "tools",
                label: (
                  <div className="flex items-center gap-2">
                    <Wrench className="w-4 h-4 text-purple-500" />
                    <span className="font-medium">Custom Tool Choice</span>
                  </div>
                ),
                children: (
                  <div className="space-y-4">
                    <TextArea
                      value={JSON.stringify(
                        (component.config as any).tool_choice,
                        null,
                        2
                      )}
                      onChange={(e) => {
                        try {
                          const value = JSON.parse(e.target.value);
                          handleConfigUpdate("tool_choice" as FieldName, value);
                        } catch (err) {
                          // Handle invalid JSON
                          console.error("Invalid JSON for tool_choice");
                        }
                      }}
                      placeholder="Enter tool choice configuration as JSON"
                      rows={4}
                    />
                  </div>
                ),
              },
            ]
          : []),
      ]}
    />
  );
};

export default React.memo(ModelFields);
