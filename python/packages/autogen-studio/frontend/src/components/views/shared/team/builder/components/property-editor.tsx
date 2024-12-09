import React, { useEffect, useMemo, useState } from "react";
import { Form, Input, Select, InputNumber, Switch, Drawer } from "antd";
import { PropertyEditorProps } from "../types";
import {
  TeamConfig,
  AgentConfig,
  ModelConfig,
  ToolConfig,
  ComponentTypes,
} from "../../../../../types/datamodel";
import { DefaultOptionType } from "antd/lib/select";

// Define the field mapping type more strictly
type FieldType = {
  name: string;
  type: "input" | "textarea" | "select" | "number" | "switch";
  label: string;
  required?: boolean;
  options?: DefaultOptionType[];
};

type FieldMappings = {
  [K in ComponentTypes]: FieldType[];
};

// Field definitions for different node types
const fieldMappings: FieldMappings = {
  team: [
    { name: "name", type: "input", label: "Name", required: true },
    {
      name: "team_type",
      type: "select",
      label: "Team Type",
      options: [
        { label: "Round Robin", value: "RoundRobinGroupChat" },
        { label: "Selector", value: "SelectorGroupChat" },
      ],
      required: true,
    },
    { name: "selector_prompt", type: "textarea", label: "Selector Prompt" },
  ],
  agent: [
    { name: "name", type: "input", label: "Name", required: true },
    {
      name: "agent_type",
      type: "select",
      label: "Agent Type",
      options: [
        { label: "Assistant", value: "AssistantAgent" },
        { label: "Coding Assistant", value: "CodingAssistantAgent" },
        { label: "Multimodal Web Surfer", value: "MultimodalWebSurfer" },
      ],
      required: true,
    },
    { name: "system_message", type: "textarea", label: "System Message" },
    { name: "description", type: "textarea", label: "Description" },
  ],
  model: [
    { name: "model", type: "input", label: "Model", required: true },
    {
      name: "model_type",
      type: "select",
      label: "Model Type",
      options: [{ label: "OpenAI Chat", value: "OpenAIChatCompletionClient" }],
      required: true,
    },
    { name: "api_key", type: "input", label: "API Key" },
    { name: "base_url", type: "input", label: "Base URL" },
  ],
  tool: [], // Add empty array for tool type
  termination: [], // Add empty array for termination type
};

export const PropertyEditor: React.FC<PropertyEditorProps> = ({
  node,
  onUpdate,
}) => {
  const [form] = Form.useForm();
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    if (node) {
      setIsOpen(true);
    }
  }, [node]);

  const fields = useMemo(() => {
    if (!node) return [];
    return fieldMappings[node.data.type] || [];
  }, [node]);

  const handleValuesChange = (changedValues: any) => {
    if (!node) return;
    const newConfig = {
      ...node.data.config,
      ...changedValues,
    };
    onUpdate({ config: newConfig });
  };

  const renderField = (field: FieldType) => {
    const baseProps = {
      label: field.label,
      required: field.required,
    };

    switch (field.type) {
      case "input":
        return <Input {...baseProps} />;
      case "textarea":
        return <Input.TextArea {...baseProps} rows={4} />;
      case "select":
        return <Select {...baseProps} options={field.options} />;
      case "number":
        return <InputNumber {...baseProps} />;
      case "switch":
        return <Switch />;
      default:
        return null;
    }
  };

  if (!node) return null;

  return (
    <Drawer
      title={`Edit ${node.data.label}`}
      placement="right"
      width={500}
      open={!!node && isOpen}
      onClose={() => setIsOpen(false)}
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={node.data.config}
        onValuesChange={handleValuesChange}
      >
        {fields.map((field) => (
          <Form.Item
            key={field.name}
            name={field.name}
            label={field.label}
            required={field.required}
          >
            {renderField(field)}
          </Form.Item>
        ))}
      </Form>
    </Drawer>
  );
};
