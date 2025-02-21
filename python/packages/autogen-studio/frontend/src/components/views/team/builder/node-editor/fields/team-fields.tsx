import React from "react";
import { Form, Input, InputNumber, Switch } from "antd";
import { isSelectorTeam, isRoundRobinTeam } from "../../../../../types/guards";
import { NestedComponentButton, NodeEditorFieldsProps } from "./fields";
const { TextArea } = Input;

export const TeamFields: React.FC<NodeEditorFieldsProps> = ({
  component,
  onNavigate,
  workingCopy,
  setWorkingCopy,
  editPath,
  updateComponentAtPath,
  getCurrentComponent,
}) => {
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
        {component.config.model_client && (
          <NestedComponentButton
            label="Model Client"
            component={component.config.model_client}
            parentField="model_client"
            onNavigate={onNavigate}
          />
        )}
        {component.config.termination_condition && (
          <NestedComponentButton
            label="Termination Condition"
            component={component.config.termination_condition}
            parentField="termination_condition"
            onNavigate={onNavigate}
          />
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
        {component.config.termination_condition && (
          <NestedComponentButton
            label="Termination Condition"
            component={component.config.termination_condition}
            parentField="termination_condition"
            onNavigate={onNavigate}
          />
        )}
      </>
    );
  }

  return null;
};
