// fields/termination-fields.tsx
import React from "react";
import { Form, Input, InputNumber } from "antd";
import { Component, ComponentConfig } from "../../../../../types/datamodel";
import {
  isOrTermination,
  isMaxMessageTermination,
  isTextMentionTermination,
} from "../../../../../types/guards";
import { NestedComponentButton } from "./fields";

interface TerminationFieldsProps {
  component: Component<ComponentConfig>;
  onNavigate: (componentType: string, id: string, parentField: string) => void;
}

export const TerminationFields: React.FC<TerminationFieldsProps> = ({
  component,
  onNavigate,
}) => {
  if (!component) return null;

  if (isOrTermination(component)) {
    return (
      <>
        <Form.Item label="Number of Conditions" name={["config", "conditions"]}>
          <InputNumber disabled />
        </Form.Item>
        {component.config.conditions &&
          component.config.conditions.length > 0 && (
            <NestedComponentButton
              label="Conditions"
              component={component.config.conditions}
              parentField="conditions"
              onNavigate={onNavigate}
            />
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

export default TerminationFields;
