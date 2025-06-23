import React, { useCallback, useState } from "react";
import { Input, InputNumber, Button, Select, Tooltip, Collapse } from "antd";
import {
  PlusCircle,
  MinusCircle,
  Edit,
  HelpCircle,
  Timer,
  Settings,
  User,
} from "lucide-react";
import {
  Component,
  ComponentConfig,
  TerminationConfig,
} from "../../../../../types/datamodel";
import {
  isOrTermination,
  isMaxMessageTermination,
  isTextMentionTermination,
  isCombinationTermination,
} from "../../../../../types/guards";
import { PROVIDERS } from "../../../../../types/guards";

interface TerminationFieldsProps {
  component: Component<TerminationConfig>;
  onChange: (updates: Partial<Component<ComponentConfig>>) => void;
  onNavigate?: (componentType: string, id: string, parentField: string) => void;
}

const TERMINATION_TYPES = {
  MAX_MESSAGE: {
    label: "Max Messages",
    provider: PROVIDERS.MAX_MESSAGE,
    defaultConfig: {
      max_messages: 10,
      include_agent_event: false,
    },
  },
  TEXT_MENTION: {
    label: "Text Mention",
    provider: PROVIDERS.TEXT_MENTION,
    defaultConfig: {
      text: "TERMINATE",
    },
  },
};

const InputWithTooltip: React.FC<{
  label: string;
  tooltip: string;
  children: React.ReactNode;
}> = ({ label, tooltip, children }) => (
  <label className="block">
    <div className="flex items-center gap-2 mb-1">
      <span className="text-sm font-medium text-gray-700">{label}</span>
      <Tooltip title={tooltip}>
        <HelpCircle className="w-4 h-4 text-gray-400" />
      </Tooltip>
    </div>
    {children}
  </label>
);

export const TerminationFields: React.FC<TerminationFieldsProps> = ({
  component,
  onChange,
  onNavigate,
}) => {
  const [showAddCondition, setShowAddCondition] = useState(false);
  const [selectedConditionType, setSelectedConditionType] =
    useState<string>("");

  if (!component) return null;

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

  const createNewCondition = (type: string) => {
    const template = TERMINATION_TYPES[type as keyof typeof TERMINATION_TYPES];
    return {
      provider: template.provider,
      component_type: "termination",
      version: 1,
      component_version: 1,
      description: `${template.label} termination condition`,
      label: template.label,
      config: template.defaultConfig,
    };
  };

  const handleAddCondition = () => {
    if (!selectedConditionType || !isCombinationTermination(component)) return;

    const newCondition = createNewCondition(selectedConditionType);
    const currentConditions = component.config.conditions || [];

    handleComponentUpdate({
      config: {
        conditions: [...currentConditions, newCondition],
      },
    });

    setShowAddCondition(false);
    setSelectedConditionType("");
  };

  const handleRemoveCondition = (index: number) => {
    if (!isCombinationTermination(component)) return;

    const currentConditions = [...component.config.conditions];
    currentConditions.splice(index, 1);

    handleComponentUpdate({
      config: {
        conditions: currentConditions,
      },
    });
  };

  if (isCombinationTermination(component)) {
    return (
      <Collapse
        defaultActiveKey={["conditions"]}
        className="border-0"
        expandIconPosition="end"
        items={[
          {
            key: "conditions",
            label: (
              <div className="flex items-center gap-2">
                <Timer className="w-4 h-4 text-blue-500" />
                <span className="font-medium">Termination Conditions</span>
              </div>
            ),
            children: (
              <div className="space-y-4">
                <div className="flex justify-between items-center">
                  <Button
                    type="dashed"
                    onClick={() => setShowAddCondition(true)}
                    icon={<PlusCircle className="w-4 h-4" />}
                    className="w-full"
                  >
                    Add Condition
                  </Button>
                </div>

                {showAddCondition && (
                  <div className="border rounded p-4 space-y-4">
                    <InputWithTooltip
                      label="Condition Type"
                      tooltip="Select the type of termination condition to add"
                    >
                      <Select
                        value={selectedConditionType}
                        onChange={setSelectedConditionType}
                        className="w-full"
                      >
                        {Object.entries(TERMINATION_TYPES).map(
                          ([key, value]) => (
                            <Select.Option key={key} value={key}>
                              {value.label}
                            </Select.Option>
                          )
                        )}
                      </Select>
                    </InputWithTooltip>
                    <Button
                      onClick={handleAddCondition}
                      disabled={!selectedConditionType}
                      className="w-full"
                    >
                      Add
                    </Button>
                  </div>
                )}

                <div className="space-y-2">
                  {component.config.conditions?.map((condition, index) => (
                    <div key={index} className="flex items-center gap-2">
                      <Button
                        onClick={() =>
                          onNavigate?.(
                            condition.component_type,
                            condition.label || "",
                            "conditions"
                          )
                        }
                        className="w-full flex justify-between items-center"
                      >
                        <span>
                          {condition.label || `Condition ${index + 1}`}
                        </span>
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button
                        type="text"
                        danger
                        icon={<MinusCircle className="w-4 h-4" />}
                        onClick={() => handleRemoveCondition(index)}
                      />
                    </div>
                  ))}
                </div>
              </div>
            ),
          },
        ]}
      />
    );
  }

  if (isMaxMessageTermination(component)) {
    return (
      <Collapse
        defaultActiveKey={["configuration"]}
        className="border-0"
        expandIconPosition="end"
        items={[
          {
            key: "configuration",
            label: (
              <div className="flex items-center gap-2">
                <Settings className="w-4 h-4 text-green-500" />
                <span className="font-medium">Max Messages Configuration</span>
              </div>
            ),
            children: (
              <InputWithTooltip
                label="Max Messages"
                tooltip="Maximum number of messages before termination"
              >
                <InputNumber
                  min={1}
                  value={component.config.max_messages}
                  onChange={(value) =>
                    handleComponentUpdate({
                      config: { max_messages: value },
                    })
                  }
                  className="w-full"
                />
              </InputWithTooltip>
            ),
          },
        ]}
      />
    );
  }

  if (isTextMentionTermination(component)) {
    return (
      <Collapse
        defaultActiveKey={["configuration"]}
        className="border-0"
        expandIconPosition="end"
        items={[
          {
            key: "configuration",
            label: (
              <div className="flex items-center gap-2">
                <Settings className="w-4 h-4 text-purple-500" />
                <span className="font-medium">Text Mention Configuration</span>
              </div>
            ),
            children: (
              <InputWithTooltip
                label="Termination Text"
                tooltip="Text that triggers termination when mentioned"
              >
                <Input
                  value={component.config.text}
                  onChange={(e) =>
                    handleComponentUpdate({
                      config: { text: e.target.value },
                    })
                  }
                />
              </InputWithTooltip>
            ),
          },
        ]}
      />
    );
  }

  return null;
};

export default React.memo(TerminationFields);
