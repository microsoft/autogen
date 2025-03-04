// fields/model-fields.tsx
import React from "react";
import { Form, Input, InputNumber, Select } from "antd";
import { Component, ComponentConfig } from "../../../../../types/datamodel";
import { isOpenAIModel, isAzureOpenAIModel } from "../../../../../types/guards";

interface ModelFieldsProps {
  component: Component<ComponentConfig>;
}

export const ModelFields: React.FC<ModelFieldsProps> = ({ component }) => {
  if (!component) return null;

  // Common arguments fields shared between OpenAI and Azure OpenAI models
  const ArgumentsFields = () => (
    <>
      <Form.Item
        label="Temperature"
        name={["config", "temperature"]}
        tooltip="Controls randomness in the model's output. Higher values (e.g., 0.8) make output more random, lower values (e.g., 0.2) make it more focused."
      >
        <InputNumber min={0} max={2} step={0.1} />
      </Form.Item>

      <Form.Item
        label="Max Tokens"
        name={["config", "max_tokens"]}
        tooltip="Maximum length of the model's output in tokens"
      >
        <InputNumber min={1} />
      </Form.Item>

      <Form.Item
        label="Top P"
        name={["config", "top_p"]}
        tooltip="Controls diversity via nucleus sampling. Lower values (e.g., 0.1) make output more focused, higher values (e.g., 0.9) make it more diverse."
      >
        <InputNumber min={0} max={1} step={0.1} />
      </Form.Item>

      <Form.Item
        label="Frequency Penalty"
        name={["config", "frequency_penalty"]}
        tooltip="Decreases the model's likelihood to repeat the same information. Values range from -2.0 to 2.0."
      >
        <InputNumber min={-2} max={2} step={0.1} />
      </Form.Item>

      <Form.Item
        label="Presence Penalty"
        name={["config", "presence_penalty"]}
        tooltip="Increases the model's likelihood to talk about new topics. Values range from -2.0 to 2.0."
      >
        <InputNumber min={-2} max={2} step={0.1} />
      </Form.Item>

      <Form.Item
        label="Stop Sequences"
        name={["config", "stop"]}
        tooltip="Sequences where the model will stop generating further tokens"
      >
        <Select
          mode="tags"
          placeholder="Enter stop sequences"
          style={{ width: "100%" }}
        />
      </Form.Item>
    </>
  );

  if (isOpenAIModel(component)) {
    return (
      <>
        <Form.Item
          label="Model"
          name={["config", "model"]}
          rules={[{ required: true }]}
          tooltip="The name of the OpenAI model to use (e.g., gpt-4, gpt-3.5-turbo)"
        >
          <Input />
        </Form.Item>

        <Form.Item
          label="API Key"
          name={["config", "api_key"]}
          tooltip="Your OpenAI API key"
        >
          <Input.Password />
        </Form.Item>

        <Form.Item
          label="Organization"
          name={["config", "organization"]}
          tooltip="Optional: Your OpenAI organization ID"
        >
          <Input />
        </Form.Item>

        <Form.Item
          label="Base URL"
          name={["config", "base_url"]}
          tooltip="Optional: Custom base URL for API requests"
        >
          <Input />
        </Form.Item>

        <Form.Item
          label="Timeout"
          name={["config", "timeout"]}
          tooltip="Request timeout in seconds"
        >
          <InputNumber min={1} />
        </Form.Item>

        <Form.Item
          label="Max Retries"
          name={["config", "max_retries"]}
          tooltip="Maximum number of retry attempts for failed requests"
        >
          <InputNumber min={0} />
        </Form.Item>

        <ArgumentsFields />
      </>
    );
  }

  if (isAzureOpenAIModel(component)) {
    return (
      <>
        <Form.Item
          label="Model"
          name={["config", "model"]}
          rules={[{ required: true }]}
          tooltip="The name of the Azure OpenAI model deployment"
        >
          <Input />
        </Form.Item>

        <Form.Item
          label="Azure Endpoint"
          name={["config", "azure_endpoint"]}
          rules={[{ required: true }]}
          tooltip="Your Azure OpenAI service endpoint URL"
        >
          <Input />
        </Form.Item>

        <Form.Item
          label="Azure Deployment"
          name={["config", "azure_deployment"]}
          tooltip="The name of your Azure OpenAI model deployment"
        >
          <Input />
        </Form.Item>

        <Form.Item
          label="API Version"
          name={["config", "api_version"]}
          rules={[{ required: true }]}
          tooltip="Azure OpenAI API version (e.g., 2023-05-15)"
        >
          <Input />
        </Form.Item>

        <Form.Item
          label="Azure AD Token"
          name={["config", "azure_ad_token"]}
          tooltip="Optional: Azure Active Directory token for authentication"
        >
          <Input.Password />
        </Form.Item>

        <ArgumentsFields />
      </>
    );
  }

  return null;
};

export default ModelFields;
