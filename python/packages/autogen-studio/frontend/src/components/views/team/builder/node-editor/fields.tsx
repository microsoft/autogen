import React from "react";
import { Input, Select, Switch, InputNumber, Form, Button } from "antd";
import { Edit } from "lucide-react";
import {
  isTeamComponent,
  isAgentComponent,
  isModelComponent,
  isToolComponent,
  isTerminationComponent,
  isSelectorTeam,
  isRoundRobinTeam,
  isAssistantAgent,
  isUserProxyAgent,
  isWebSurferAgent,
  isOpenAIModel,
  isAzureOpenAIModel,
  isFunctionTool,
  isOrTermination,
  isMaxMessageTermination,
  isTextMentionTermination,
} from "../../../../types/guards";
import { Component, ComponentConfig } from "../../../../types/datamodel";
import DetailGroup from "./detailgroup";

const { TextArea } = Input;
const { Option } = Select;

interface NodeEditorFieldsProps {
  component: Component<ComponentConfig>;
  onNavigate: (componentType: string, id: string, parentField: string) => void;
}

export const NodeEditorFields: React.FC<NodeEditorFieldsProps> = ({
  component,
  onNavigate,
}) => {
  const renderNestedComponentButton = (
    label: string,
    component: Component<ComponentConfig> | Component<ComponentConfig>[],
    parentField: string
  ) => {
    if (Array.isArray(component)) {
      return (
        <div className="space-y-2 mb-4">
          <div className="flex justify-between items-center">
            <span className="text-sm font-medium">{label}</span>
          </div>
          {component.map((item) => (
            <Button
              key={item.label}
              onClick={() =>
                onNavigate(item.component_type, item.label || "", parentField)
              }
              className="w-full flex justify-between items-center"
            >
              <span>{item.label}</span>
              <Edit className="w-4 h-4" />
            </Button>
          ))}
        </div>
      );
    }

    return component ? (
      <div className="mb-4">
        <Button
          onClick={() =>
            onNavigate(
              component.component_type,
              component.label || "",
              parentField
            )
          }
          className="w-full flex justify-between items-center"
        >
          <span>{label}</span>
          <Edit className="w-4 h-4" />
        </Button>
      </div>
    ) : null;
  };

  const renderTeamFields = () => {
    if (!component) return null;

    if (isSelectorTeam(component)) {
      return (
        <>
          <Form.Item
            label="Selector Prompt"
            name={["config", "selector_prompt"]}
            rules={[{ required: true }]}
          >
            <TextArea rows={4} />
          </Form.Item>
          <Form.Item label="Max Turns" name={["config", "max_turns"]}>
            <InputNumber min={1} />
          </Form.Item>
          <Form.Item
            label="Allow Repeated Speaker"
            name={["config", "allow_repeated_speaker"]}
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
          {component.config.model_client &&
            renderNestedComponentButton(
              "Model Client",
              component.config.model_client,
              "model_client"
            )}
          {component.config.termination_condition &&
            renderNestedComponentButton(
              "Termination Condition",
              component.config.termination_condition,
              "termination_condition"
            )}
        </>
      );
    }
    if (isRoundRobinTeam(component)) {
      return (
        <>
          <Form.Item label="Max Turns" name={["config", "max_turns"]}>
            <InputNumber min={1} />
          </Form.Item>
          {component.config.termination_condition &&
            renderNestedComponentButton(
              "Termination Condition",
              component.config.termination_condition,
              "termination_condition"
            )}
        </>
      );
    }
    return null;
  };

  const renderAgentFields = () => {
    if (!component) return null;

    if (isAssistantAgent(component)) {
      return (
        <>
          <Form.Item
            label="Name"
            name={["config", "name"]}
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="Description"
            name={["config", "description"]}
            rules={[{ required: true }]}
          >
            <TextArea rows={4} />
          </Form.Item>
          <Form.Item label="System Message" name={["config", "system_message"]}>
            <TextArea rows={4} />
          </Form.Item>
          <Form.Item
            label="Reflect on Tool Use"
            name={["config", "reflect_on_tool_use"]}
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
          <Form.Item
            label="Tool Call Summary Format"
            name={["config", "tool_call_summary_format"]}
          >
            <Input />
          </Form.Item>
          {component.config.model_client &&
            renderNestedComponentButton(
              "Model Client",
              component.config.model_client,
              "model_client"
            )}
          {component.config.tools &&
            component.config.tools.length > 0 &&
            renderNestedComponentButton(
              "Tools",
              component.config.tools,
              "tools"
            )}
        </>
      );
    }
    if (isUserProxyAgent(component)) {
      return (
        <>
          <Form.Item
            label="Name"
            name={["config", "name"]}
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="Description"
            name={["config", "description"]}
            rules={[{ required: true }]}
          >
            <TextArea rows={4} />
          </Form.Item>
        </>
      );
    }
    if (isWebSurferAgent(component)) {
      return (
        <>
          <Form.Item
            label="Name"
            name={["config", "name"]}
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="Downloads Folder"
            name={["config", "downloads_folder"]}
          >
            <Input />
          </Form.Item>
          <Form.Item label="Description" name={["config", "description"]}>
            <TextArea rows={4} />
          </Form.Item>
          <Form.Item label="Start Page" name={["config", "start_page"]}>
            <Input />
          </Form.Item>
          <Form.Item
            label="Headless"
            name={["config", "headless"]}
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
          <Form.Item
            label="Animate Actions"
            name={["config", "animate_actions"]}
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
          <Form.Item
            label="Save Screenshots"
            name={["config", "to_save_screenshots"]}
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
          <Form.Item
            label="Use OCR"
            name={["config", "use_ocr"]}
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
          <Form.Item
            label="Browser Channel"
            name={["config", "browser_channel"]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="Browser Data Directory"
            name={["config", "browser_data_dir"]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="Resize Viewport"
            name={["config", "to_resize_viewport"]}
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
          {component.config.model_client &&
            renderNestedComponentButton(
              "Model Client",
              component.config.model_client,
              "model_client"
            )}
        </>
      );
    }
    return null;
  };

  const renderModelFields = () => {
    if (!component) return null;

    const createArgumentsFields = (
      <>
        <Form.Item label="Temperature" name={["config", "temperature"]}>
          <InputNumber min={0} max={2} step={0.1} />
        </Form.Item>
        <Form.Item label="Max Tokens" name={["config", "max_tokens"]}>
          <InputNumber min={1} />
        </Form.Item>
        <Form.Item label="Top P" name={["config", "top_p"]}>
          <InputNumber min={0} max={1} step={0.1} />
        </Form.Item>
        <Form.Item
          label="Frequency Penalty"
          name={["config", "frequency_penalty"]}
        >
          <InputNumber min={-2} max={2} step={0.1} />
        </Form.Item>
        <Form.Item
          label="Presence Penalty"
          name={["config", "presence_penalty"]}
        >
          <InputNumber min={-2} max={2} step={0.1} />
        </Form.Item>
        <Form.Item label="Stop Sequences" name={["config", "stop"]}>
          <Select mode="tags" />
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
          >
            <Input />
          </Form.Item>
          <Form.Item label="API Key" name={["config", "api_key"]}>
            <Input.Password />
          </Form.Item>
          <Form.Item label="Organization" name={["config", "organization"]}>
            <Input />
          </Form.Item>
          <Form.Item label="Base URL" name={["config", "base_url"]}>
            <Input />
          </Form.Item>
          <Form.Item label="Timeout" name={["config", "timeout"]}>
            <InputNumber min={1} />
          </Form.Item>
          <Form.Item label="Max Retries" name={["config", "max_retries"]}>
            <InputNumber min={0} />
          </Form.Item>
          {createArgumentsFields}
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
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="Azure Endpoint"
            name={["config", "azure_endpoint"]}
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="Azure Deployment"
            name={["config", "azure_deployment"]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="API Version"
            name={["config", "api_version"]}
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item label="Azure AD Token" name={["config", "azure_ad_token"]}>
            <Input.Password />
          </Form.Item>
          {createArgumentsFields}
        </>
      );
    }
    return null;
  };

  const renderToolFields = () => {
    if (!component) return null;

    if (isFunctionTool(component)) {
      return (
        <>
          <Form.Item
            label="Name"
            name={["config", "name"]}
            rules={[{ required: true }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="Description"
            name={["config", "description"]}
            rules={[{ required: true }]}
          >
            <TextArea rows={4} />
          </Form.Item>
          <Form.Item
            label="Source Code"
            name={["config", "source_code"]}
            rules={[{ required: true }]}
          >
            <TextArea rows={8} />
          </Form.Item>
          <Form.Item
            label="Has Cancellation Support"
            name={["config", "has_cancellation_support"]}
            valuePropName="checked"
          >
            <Switch />
          </Form.Item>
        </>
      );
    }
    return null;
  };

  const renderTerminationFields = () => {
    if (!component) return null;

    if (isOrTermination(component)) {
      return (
        <>
          <Form.Item
            label="Number of Conditions"
            name={["config", "conditions"]}
          >
            <InputNumber disabled />
          </Form.Item>
          {component.config.conditions &&
            component.config.conditions.length > 0 &&
            renderNestedComponentButton(
              "Conditions",
              component.config.conditions,
              "conditions"
            )}
        </>
      );
    }
    if (isMaxMessageTermination(component)) {
      return (
        <Form.Item
          label="Max Messages"
          name={["config", "max_messages"]}
          rules={[{ required: true }]}
        >
          <InputNumber min={1} />
        </Form.Item>
      );
    }
    if (isTextMentionTermination(component)) {
      return (
        <Form.Item
          label="Text"
          name={["config", "text"]}
          rules={[{ required: true }]}
        >
          <Input />
        </Form.Item>
      );
    }
    return null;
  };

  // Common fields for all components
  const commonFields = (
    <DetailGroup title="Component Details">
      <Form.Item label="Label" name="label">
        <Input />
      </Form.Item>
      <Form.Item label="Description" name="description">
        <TextArea rows={4} />
      </Form.Item>
    </DetailGroup>
  );
  // Component-specific fields
  let specificFields = null;
  if (isTeamComponent(component)) {
    specificFields = (
      <DetailGroup title="Configuration">{renderTeamFields()}</DetailGroup>
    );
  } else if (isAgentComponent(component)) {
    specificFields = (
      <DetailGroup title="Configuration">{renderAgentFields()}</DetailGroup>
    );
  } else if (isModelComponent(component)) {
    specificFields = (
      <DetailGroup title="Configuration">{renderModelFields()}</DetailGroup>
    );
  } else if (isToolComponent(component)) {
    specificFields = (
      <DetailGroup title="Configuration">{renderToolFields()}</DetailGroup>
    );
  } else if (isTerminationComponent(component)) {
    specificFields = (
      <DetailGroup title="Configuration">
        {renderTerminationFields()}
      </DetailGroup>
    );
  }
  return (
    <>
      {commonFields}
      {specificFields}
    </>
  );
};

export default NodeEditorFields;
