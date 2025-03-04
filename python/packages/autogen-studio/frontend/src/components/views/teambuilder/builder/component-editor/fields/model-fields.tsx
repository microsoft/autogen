import React, { useCallback } from "react";
import { Input, InputNumber, Select, Tooltip } from "antd";
import { HelpCircle } from "lucide-react";
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
import DetailGroup from "../detailgroup";
import TextArea from "antd/es/input/TextArea";

interface ModelFieldsProps {
  component: Component<ModelConfig>;
  onChange: (updates: Partial<Component<ComponentConfig>>) => void;
}

const InputWithTooltip: React.FC<{
  label: string;
  tooltip: string;
  children: React.ReactNode;
}> = ({ label, tooltip, children }) => (
  <label className="block">
    <div className="flex items-center gap-2 mb-1">
      <span className="text-sm font-medium text-primary">{label}</span>
      <Tooltip title={tooltip}>
        <HelpCircle className="w-4 h-4 text-secondary" />
      </Tooltip>
    </div>
    {children}
  </label>
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
  | "metadata";

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

// Field specifications for all possible model parameters
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
};

// Define provider field mapping type
type ProviderType = "openai" | "azure" | "anthropic";

interface ProviderFields {
  modelConfig: FieldName[];
  modelParams: FieldName[];
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
    <div className="space-y-6">
      <DetailGroup title="Component Details">
        <div className="space-y-4">
          <label className="block">
            <span className="text-sm font-medium text-primary">Name</span>
            <Input
              value={component.label || ""}
              onChange={(e) => handleComponentUpdate({ label: e.target.value })}
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
      </DetailGroup>

      <DetailGroup
        title={
          providerType === "azure"
            ? "Azure Configuration"
            : "Model Configuration"
        }
      >
        {renderFieldGroup(providerFields[providerType].modelConfig)}
      </DetailGroup>

      <DetailGroup title="Model Parameters">
        {renderFieldGroup(providerFields[providerType].modelParams)}
      </DetailGroup>

      {/* Only render tool configuration if it's an Anthropic model and has tools */}
      {providerType === "anthropic" &&
        (component.config as any).tool_choice === "custom" && (
          <DetailGroup title="Custom Tool Choice">
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
          </DetailGroup>
        )}
    </div>
  );
};

export default React.memo(ModelFields);
