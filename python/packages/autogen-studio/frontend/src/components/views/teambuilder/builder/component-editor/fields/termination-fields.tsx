import React, { useCallback, useState } from "react";
import {
  Input,
  InputNumber,
  Button,
  Select,
  Tooltip,
  Collapse,
  Checkbox,
} from "antd";
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
  TokenUsageTerminationConfig,
  TimeoutTerminationConfig,
  HandoffTerminationConfig,
  SourceMatchTerminationConfig,
  TextMessageTerminationConfig,
  ExternalTerminationConfig,
} from "../../../../../types/datamodel";
import {
  isOrTermination,
  isMaxMessageTermination,
  isTextMentionTermination,
  isCombinationTermination,
  isStopMessageTermination,
  isTokenUsageTermination,
  isHandoffTermination,
  isTimeoutTermination,
  isExternalTermination,
  isSourceMatchTermination,
  isTextMessageTermination,
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
  STOP_MESSAGE: {
    label: "Stop Message",
    provider: PROVIDERS.STOP_MESSAGE,
    defaultConfig: {},
  },
  TOKEN_USAGE: {
    label: "Token Usage",
    provider: PROVIDERS.TOKEN_USAGE,
    defaultConfig: {
      max_total_token: 1000,
    },
  },
  TIMEOUT: {
    label: "Timeout",
    provider: PROVIDERS.TIMEOUT,
    defaultConfig: {
      timeout_seconds: 300,
    },
  },
  HANDOFF: {
    label: "Handoff",
    provider: PROVIDERS.HANDOFF,
    defaultConfig: {
      target: "",
    },
  },
  SOURCE_MATCH: {
    label: "Source Match",
    provider: PROVIDERS.SOURCE_MATCH,
    defaultConfig: {
      sources: [],
    },
  },
  TEXT_MESSAGE: {
    label: "Text Message",
    provider: PROVIDERS.TEXT_MESSAGE,
    defaultConfig: {
      source: "",
    },
  },
  EXTERNAL: {
    label: "External",
    provider: PROVIDERS.EXTERNAL,
    defaultConfig: {},
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
              <div className="space-y-4">
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
                <InputWithTooltip
                  label="Include Agent Events"
                  tooltip="Include agent events in the message count, not just chat messages"
                >
                  <Checkbox
                    checked={component.config.include_agent_event || false}
                    onChange={(e) =>
                      handleComponentUpdate({
                        config: { include_agent_event: e.target.checked },
                      })
                    }
                  >
                    Include agent events in message count
                  </Checkbox>
                </InputWithTooltip>
              </div>
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

  if (isStopMessageTermination(component)) {
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
                <Settings className="w-4 h-4 text-red-500" />
                <span className="font-medium">Stop Message Configuration</span>
              </div>
            ),
            children: (
              <div className="text-sm text-gray-600">
                This termination condition triggers when a StopMessage is
                received. No additional configuration is required.
              </div>
            ),
          },
        ]}
      />
    );
  }

  if (isTokenUsageTermination(component)) {
    const tokenComponent = component as Component<TokenUsageTerminationConfig>;
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
                <Settings className="w-4 h-4 text-yellow-500" />
                <span className="font-medium">Token Usage Configuration</span>
              </div>
            ),
            children: (
              <div className="space-y-4">
                <InputWithTooltip
                  label="Max Total Tokens"
                  tooltip="Maximum total number of tokens allowed"
                >
                  <InputNumber
                    min={1}
                    value={tokenComponent.config.max_total_token}
                    onChange={(value) =>
                      handleComponentUpdate({
                        config: { max_total_token: value },
                      })
                    }
                    className="w-full"
                    placeholder="e.g., 1000"
                  />
                </InputWithTooltip>
                <InputWithTooltip
                  label="Max Prompt Tokens"
                  tooltip="Maximum number of prompt tokens allowed"
                >
                  <InputNumber
                    min={1}
                    value={tokenComponent.config.max_prompt_token}
                    onChange={(value) =>
                      handleComponentUpdate({
                        config: { max_prompt_token: value },
                      })
                    }
                    className="w-full"
                    placeholder="e.g., 800"
                  />
                </InputWithTooltip>
                <InputWithTooltip
                  label="Max Completion Tokens"
                  tooltip="Maximum number of completion tokens allowed"
                >
                  <InputNumber
                    min={1}
                    value={tokenComponent.config.max_completion_token}
                    onChange={(value) =>
                      handleComponentUpdate({
                        config: { max_completion_token: value },
                      })
                    }
                    className="w-full"
                    placeholder="e.g., 200"
                  />
                </InputWithTooltip>
              </div>
            ),
          },
        ]}
      />
    );
  }

  if (isTimeoutTermination(component)) {
    const timeoutComponent = component as Component<TimeoutTerminationConfig>;
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
                <Timer className="w-4 h-4 text-orange-500" />
                <span className="font-medium">Timeout Configuration</span>
              </div>
            ),
            children: (
              <InputWithTooltip
                label="Timeout (seconds)"
                tooltip="Maximum duration in seconds before termination"
              >
                <InputNumber
                  min={1}
                  value={timeoutComponent.config.timeout_seconds}
                  onChange={(value) =>
                    handleComponentUpdate({
                      config: { timeout_seconds: value },
                    })
                  }
                  className="w-full"
                  placeholder="e.g., 300"
                />
              </InputWithTooltip>
            ),
          },
        ]}
      />
    );
  }

  if (isHandoffTermination(component)) {
    const handoffComponent = component as Component<HandoffTerminationConfig>;
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
                <User className="w-4 h-4 text-blue-500" />
                <span className="font-medium">Handoff Configuration</span>
              </div>
            ),
            children: (
              <InputWithTooltip
                label="Target Agent"
                tooltip="Agent to handoff to before termination"
              >
                <Input
                  value={handoffComponent.config.target}
                  onChange={(e) =>
                    handleComponentUpdate({
                      config: { target: e.target.value },
                    })
                  }
                  placeholder="e.g., agent_name"
                />
              </InputWithTooltip>
            ),
          },
        ]}
      />
    );
  }

  if (isSourceMatchTermination(component)) {
    const sourceMatchComponent =
      component as Component<SourceMatchTerminationConfig>;
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
                <Settings className="w-4 h-4 text-indigo-500" />
                <span className="font-medium">Source Match Configuration</span>
              </div>
            ),
            children: (
              <InputWithTooltip
                label="Source Names"
                tooltip="List of source names to match (comma-separated)"
              >
                <Input
                  value={sourceMatchComponent.config.sources?.join(", ") || ""}
                  onChange={(e) =>
                    handleComponentUpdate({
                      config: {
                        sources: e.target.value
                          .split(",")
                          .map((s) => s.trim())
                          .filter((s) => s.length > 0),
                      },
                    })
                  }
                  placeholder="e.g., agent1, agent2"
                />
              </InputWithTooltip>
            ),
          },
        ]}
      />
    );
  }

  if (isTextMessageTermination(component)) {
    const textMessageComponent =
      component as Component<TextMessageTerminationConfig>;
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
                <Settings className="w-4 h-4 text-pink-500" />
                <span className="font-medium">Text Message Configuration</span>
              </div>
            ),
            children: (
              <InputWithTooltip
                label="Source Filter (optional)"
                tooltip="Filter to only terminate on text messages from specific source"
              >
                <Input
                  value={textMessageComponent.config.source || ""}
                  onChange={(e) =>
                    handleComponentUpdate({
                      config: { source: e.target.value || undefined },
                    })
                  }
                  placeholder="e.g., agent_name (leave empty for any source)"
                />
              </InputWithTooltip>
            ),
          },
        ]}
      />
    );
  }

  if (isExternalTermination(component)) {
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
                <Settings className="w-4 h-4 text-gray-500" />
                <span className="font-medium">
                  External Termination Configuration
                </span>
              </div>
            ),
            children: (
              <div className="text-sm text-gray-600">
                This termination condition is controlled externally by calling
                the set() method. No additional configuration is required.
              </div>
            ),
          },
        ]}
      />
    );
  }

  return null;
};

export default React.memo(TerminationFields);
