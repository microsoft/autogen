import React, { useCallback } from "react";
import { Input, InputNumber, Select, Tooltip } from "antd";
import { HelpCircle } from "lucide-react";
import {
  Component,
  ComponentConfig,
  ModelConfig,
} from "../../../../../types/datamodel";
import { isOpenAIModel, isAzureOpenAIModel } from "../../../../../types/guards";
import DetailGroup from "../detailgroup";
import TextArea from "antd/es/input/TextArea";
// import DetailGroup from "./detail-group";

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

export const ModelFields: React.FC<ModelFieldsProps> = ({
  component,
  onChange,
}) => {
  if (!isOpenAIModel(component) && !isAzureOpenAIModel(component)) return null;

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
    (field: string, value: unknown) => {
      handleComponentUpdate({
        config: {
          ...component.config,
          [field]: value,
        },
      });
    },
    [component, handleComponentUpdate]
  );

  // Common arguments fields shared between OpenAI and Azure OpenAI models
  const ArgumentsFields = () => (
    <div className="space-y-4">
      <InputWithTooltip
        label="Temperature"
        tooltip="Controls randomness in the model's output. Higher values (e.g., 0.8) make output more random, lower values (e.g., 0.2) make it more focused."
      >
        <InputNumber
          min={0}
          max={2}
          step={0.1}
          value={component.config.temperature}
          onChange={(value) => handleConfigUpdate("temperature", value)}
          className="w-full"
        />
      </InputWithTooltip>

      <InputWithTooltip
        label="Max Tokens"
        tooltip="Maximum length of the model's output in tokens"
      >
        <InputNumber
          min={1}
          value={component.config.max_tokens}
          onChange={(value) => handleConfigUpdate("max_tokens", value)}
          className="w-full"
        />
      </InputWithTooltip>

      <InputWithTooltip
        label="Top P"
        tooltip="Controls diversity via nucleus sampling. Lower values (e.g., 0.1) make output more focused, higher values (e.g., 0.9) make it more diverse."
      >
        <InputNumber
          min={0}
          max={1}
          step={0.1}
          value={component.config.top_p}
          onChange={(value) => handleConfigUpdate("top_p", value)}
          className="w-full"
        />
      </InputWithTooltip>

      <InputWithTooltip
        label="Frequency Penalty"
        tooltip="Decreases the model's likelihood to repeat the same information. Values range from -2.0 to 2.0."
      >
        <InputNumber
          min={-2}
          max={2}
          step={0.1}
          value={component.config.frequency_penalty}
          onChange={(value) => handleConfigUpdate("frequency_penalty", value)}
          className="w-full"
        />
      </InputWithTooltip>

      <InputWithTooltip
        label="Presence Penalty"
        tooltip="Increases the model's likelihood to talk about new topics. Values range from -2.0 to 2.0."
      >
        <InputNumber
          min={-2}
          max={2}
          step={0.1}
          value={component.config.presence_penalty}
          onChange={(value) => handleConfigUpdate("presence_penalty", value)}
          className="w-full"
        />
      </InputWithTooltip>

      <InputWithTooltip
        label="Stop Sequences"
        tooltip="Sequences where the model will stop generating further tokens"
      >
        <Select
          mode="tags"
          value={component.config.stop as string[]}
          onChange={(value) => handleConfigUpdate("stop", value)}
          placeholder="Enter stop sequences"
          className="w-full"
        />
      </InputWithTooltip>
    </div>
  );

  if (isOpenAIModel(component)) {
    return (
      <div className="space-y-6">
        <DetailGroup title="Component Details">
          <div className="space-y-4">
            <label className="block">
              <span className="text-sm font-medium text-primary">Name</span>
              <Input
                value={component.label || ""}
                onChange={(e) =>
                  handleComponentUpdate({ label: e.target.value })
                }
                placeholder="Team name"
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
                placeholder="Team description"
                rows={4}
                className="mt-1"
              />
            </label>
          </div>
        </DetailGroup>

        <DetailGroup title="Model Configuration">
          <div className="space-y-4">
            <InputWithTooltip
              label="Model"
              tooltip="The name of the OpenAI model to use (e.g., gpt-4, gpt-3.5-turbo)"
            >
              <Input
                value={component.config.model}
                onChange={(e) => handleConfigUpdate("model", e.target.value)}
                required
              />
            </InputWithTooltip>

            <InputWithTooltip label="API Key" tooltip="Your OpenAI API key">
              <Input.Password
                value={component.config.api_key}
                onChange={(e) => handleConfigUpdate("api_key", e.target.value)}
              />
            </InputWithTooltip>

            <InputWithTooltip
              label="Organization"
              tooltip="Optional: Your OpenAI organization ID"
            >
              <Input
                value={component.config.organization}
                onChange={(e) =>
                  handleConfigUpdate("organization", e.target.value)
                }
              />
            </InputWithTooltip>

            <InputWithTooltip
              label="Base URL"
              tooltip="Optional: Custom base URL for API requests"
            >
              <Input
                value={component.config.base_url}
                onChange={(e) => handleConfigUpdate("base_url", e.target.value)}
              />
            </InputWithTooltip>

            <InputWithTooltip
              label="Timeout"
              tooltip="Request timeout in seconds"
            >
              <InputNumber
                min={1}
                value={component.config.timeout}
                onChange={(value) => handleConfigUpdate("timeout", value)}
                className="w-full"
              />
            </InputWithTooltip>

            <InputWithTooltip
              label="Max Retries"
              tooltip="Maximum number of retry attempts for failed requests"
            >
              <InputNumber
                min={0}
                value={component.config.max_retries}
                onChange={(value) => handleConfigUpdate("max_retries", value)}
                className="w-full"
              />
            </InputWithTooltip>
          </div>
        </DetailGroup>

        <DetailGroup title="Model Parameters">
          <ArgumentsFields />
        </DetailGroup>
      </div>
    );
  }

  if (isAzureOpenAIModel(component)) {
    return (
      <div className="space-y-6">
        <DetailGroup title="Azure Configuration">
          <div className="space-y-4">
            <InputWithTooltip
              label="Model"
              tooltip="The name of the Azure OpenAI model deployment"
            >
              <Input
                value={component.config.model}
                onChange={(e) => handleConfigUpdate("model", e.target.value)}
                required
              />
            </InputWithTooltip>

            <InputWithTooltip
              label="Azure Endpoint"
              tooltip="Your Azure OpenAI service endpoint URL"
            >
              <Input
                value={component.config.azure_endpoint}
                onChange={(e) =>
                  handleConfigUpdate("azure_endpoint", e.target.value)
                }
                required
              />
            </InputWithTooltip>

            <InputWithTooltip
              label="API Key"
              tooltip="Your Azure OpenAI API key"
            >
              <Input.Password
                value={component.config.api_key}
                onChange={(e) => handleConfigUpdate("api_key", e.target.value)}
              />
            </InputWithTooltip>

            <InputWithTooltip
              label="Azure Deployment"
              tooltip="The name of your Azure OpenAI model deployment"
            >
              <Input
                value={component.config.azure_deployment}
                onChange={(e) =>
                  handleConfigUpdate("azure_deployment", e.target.value)
                }
              />
            </InputWithTooltip>

            <InputWithTooltip
              label="API Version"
              tooltip="Azure OpenAI API version (e.g., 2023-05-15)"
            >
              <Input
                value={component.config.api_version}
                onChange={(e) =>
                  handleConfigUpdate("api_version", e.target.value)
                }
                required
              />
            </InputWithTooltip>

            <InputWithTooltip
              label="Azure AD Token"
              tooltip="Optional: Azure Active Directory token for authentication"
            >
              <Input.Password
                value={component.config.azure_ad_token}
                onChange={(e) =>
                  handleConfigUpdate("azure_ad_token", e.target.value)
                }
              />
            </InputWithTooltip>
          </div>
        </DetailGroup>

        <DetailGroup title="Model Parameters">
          <ArgumentsFields />
        </DetailGroup>
      </div>
    );
  }

  return null;
};

export default React.memo(ModelFields);
