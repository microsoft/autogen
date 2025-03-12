import React, { useCallback, useState } from "react";
import { Input, InputNumber, Button, Select, Tooltip } from "antd";
import { PlusCircle, MinusCircle, Edit, HelpCircle } from "lucide-react";
import {
  Component,
  ComponentConfig,
  TerminationConfig,
} from "../../../../../types/datamodel";
import {
  isOrTermination,
  isMaxMessageTermination,
  isTextMentionTermination,
} from "../../../../../types/guards";
import { PROVIDERS } from "../../../../../types/guards";
import DetailGroup from "../../component-editor/detailgroup";
interface TerminationFieldsProps {
  component: Component<TerminationConfig>;
  onChange: (updates: Partial<Component<ComponentConfig>>) => void;
  onNavigate?: (
    componentType: string,
    id: string,
    parentField: string,
    index?: number
  ) => void;
  workingCopy?: Component<ComponentConfig> | null;
  setWorkingCopy?: (component: Component<ComponentConfig> | null) => void;
  editPath?: any[];
  updateComponentAtPath?: any;
  getCurrentComponent?: any;
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
      <span className="text-sm font-medium text-primary">{label}</span>
      <Tooltip title={tooltip}>
        <HelpCircle className="w-4 h-4 text-secondary" />
      </Tooltip>
    </div>
    {children}
  </label>
);

export const TerminationFields: React.FC<TerminationFieldsProps> = ({
  component,
  onChange,
  onNavigate,
  workingCopy,
  setWorkingCopy,
  editPath,
  updateComponentAtPath,
  getCurrentComponent,
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
    if (!selectedConditionType || !isOrTermination(component)) return;

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
    if (!isOrTermination(component)) return;

    const currentConditions = [...component.config.conditions];
    currentConditions.splice(index, 1);

    handleComponentUpdate({
      config: {
        conditions: currentConditions,
      },
    });
  };

  const handleNavigateToCondition = (
    condition: Component<TerminationConfig>,
    index: number
  ) => {
    if (!onNavigate) return;

    // Use both the condition ID and the array index
    const conditionId = condition.label || `condition-${index}`;

    // The critical change: pass the index to onNavigate
    onNavigate("termination", conditionId, "conditions", index);
  };

  if (isOrTermination(component)) {
    return (
      <DetailGroup title="Termination Conditions">
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
                  {Object.entries(TERMINATION_TYPES).map(([key, value]) => (
                    <Select.Option key={key} value={key}>
                      {value.label}
                    </Select.Option>
                  ))}
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
                  onClick={() => handleNavigateToCondition(condition, index)}
                  className="w-full flex justify-between items-center"
                >
                  <span>
                    {condition.label || `Condition ${index + 1}`}
                    {isMaxMessageTermination(condition) &&
                      ` (Max: ${condition.config.max_messages})`}
                    {isTextMentionTermination(condition) &&
                      ` (Text: "${condition.config.text}")`}
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
            {(!component.config.conditions ||
              component.config.conditions.length === 0) && (
              <div className="text-center p-4 text-secondary bg-secondary/20 rounded">
                No conditions added yet
              </div>
            )}
          </div>
        </div>
      </DetailGroup>
    );
  }

  if (isMaxMessageTermination(component)) {
    return (
      <DetailGroup title="Max Messages Configuration">
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
      </DetailGroup>
    );
  }

  if (isTextMentionTermination(component)) {
    return (
      <DetailGroup title="Text Mention Configuration">
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
      </DetailGroup>
    );
  }

  return null;
};

export default React.memo(TerminationFields);
