// fields/agent-fields.tsx
import React from "react";
import { Form, Input, Switch } from "antd";
import {
  isAssistantAgent,
  isUserProxyAgent,
  isWebSurferAgent,
} from "../../../../../types/guards";
import { NestedComponentButton } from "./fields";
import { NodeEditorFieldsProps } from "./fields";

const { TextArea } = Input;

export const AgentFields: React.FC<NodeEditorFieldsProps> = ({
  component,
  onNavigate,
  workingCopy,
  setWorkingCopy,
  editPath,
  updateComponentAtPath,
  getCurrentComponent,
}) => {
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
        {component.config.model_client && (
          <NestedComponentButton
            label="Model Client"
            component={component.config.model_client}
            parentField="model_client"
            onNavigate={onNavigate}
          />
        )}
        {component.config.tools && component.config.tools.length > 0 && (
          <NestedComponentButton
            label="Tools"
            component={component.config.tools}
            parentField="tools"
            onNavigate={onNavigate}
            workingCopy={workingCopy}
            setWorkingCopy={setWorkingCopy}
            editPath={editPath}
            updateComponentAtPath={updateComponentAtPath}
            getCurrentComponent={getCurrentComponent}
          />
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
        <Form.Item label="Browser Channel" name={["config", "browser_channel"]}>
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
        {component.config.model_client && (
          <NestedComponentButton
            label="Model Client"
            component={component.config.model_client}
            parentField="model_client"
            onNavigate={onNavigate}
          />
        )}
      </>
    );
  }

  return null;
};

export default AgentFields;
