import React, { useCallback } from "react";
import { Input, Button, Collapse } from "antd";
import { Edit, Timer, User, Settings } from "lucide-react";
import {
  Component,
  TeamConfig,
  ComponentConfig,
  RoundRobinGroupChatConfig,
  SelectorGroupChatConfig,
  SwarmConfig,
} from "../../../../../types/datamodel";
import {
  isSelectorTeam,
  isRoundRobinTeam,
  isSwarmTeam,
} from "../../../../../types/guards";

const { TextArea } = Input;

interface TeamFieldsProps {
  component: Component<TeamConfig>;
  onChange: (updates: Partial<Component<ComponentConfig>>) => void;
  onNavigate?: (componentType: string, id: string, parentField: string) => void;
}

export const TeamFields: React.FC<TeamFieldsProps> = ({
  component,
  onChange,
  onNavigate,
}) => {
  if (
    !isSelectorTeam(component) &&
    !isRoundRobinTeam(component) &&
    !isSwarmTeam(component)
  )
    return null;

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
      if (isSelectorTeam(component)) {
        handleComponentUpdate({
          config: {
            ...component.config,
            [field]: value,
          } as SelectorGroupChatConfig,
        });
      } else if (isRoundRobinTeam(component)) {
        handleComponentUpdate({
          config: {
            ...component.config,
            [field]: value,
          } as RoundRobinGroupChatConfig,
        });
      } else if (isSwarmTeam(component)) {
        handleComponentUpdate({
          config: {
            ...(component as Component<SwarmConfig>).config,
            [field]: value,
          } as SwarmConfig,
        });
      }
    },
    [component, handleComponentUpdate]
  );

  return (
    <Collapse
      defaultActiveKey={["details", "configuration"]}
      className="border-0"
      expandIconPosition="end"
      items={[
        {
          key: "details",
          label: (
            <div className="flex items-center gap-2">
              <User className="w-4 h-4 text-blue-500" />
              <span className="font-medium">Component Details</span>
            </div>
          ),
          children: (
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
          ),
        },
        {
          key: "configuration",
          label: (
            <div className="flex items-center gap-2">
              <Settings className="w-4 h-4 text-green-500" />
              <span className="font-medium">Team Configuration</span>
            </div>
          ),
          children: (
            <div className="space-y-4">
              {isSelectorTeam(component) && (
                <div className="space-y-4">
                  <label className="block">
                    <span className="text-sm font-medium text-primary">
                      Selector Prompt
                    </span>
                    <TextArea
                      value={component.config.selector_prompt || ""}
                      onChange={(e) =>
                        handleConfigUpdate("selector_prompt", e.target.value)
                      }
                      placeholder="Prompt for the selector"
                      rows={4}
                      className="mt-1"
                    />
                  </label>

                  <div className="space-y-2">
                    <h3 className="text-sm font-medium text-primary">Model</h3>
                    <div className="bg-secondary p-4 rounded-md">
                      {component.config.model_client ? (
                        <div className="flex items-center justify-between">
                          <span className="text-sm">
                            {component.config.model_client.config.model}
                          </span>
                          {onNavigate && (
                            <Button
                              type="text"
                              icon={<Edit className="w-4 h-4" />}
                              onClick={() =>
                                onNavigate(
                                  "model",
                                  component.config.model_client?.label || "",
                                  "model_client"
                                )
                              }
                            />
                          )}
                        </div>
                      ) : (
                        <div className="text-sm text-secondary text-center">
                          No model configured
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {isSwarmTeam(component) && (
                <div className="space-y-4">
                  <div className="space-y-2">
                    <h3 className="text-sm font-medium text-primary">
                      Team Type
                    </h3>
                    <div className="bg-secondary p-4 rounded-md">
                      <div className="text-sm text-secondary">
                        Swarm team uses handoff messages to transfer control
                        between agents. Each agent specifies which agents they
                        can hand off to.
                      </div>
                    </div>
                  </div>

                  <label className="block">
                    <span className="text-sm font-medium text-primary">
                      Emit Team Events
                    </span>
                    <div className="mt-1">
                      <input
                        type="checkbox"
                        checked={component.config.emit_team_events || false}
                        onChange={(e) =>
                          handleConfigUpdate(
                            "emit_team_events",
                            e.target.checked
                          )
                        }
                        className="mr-2"
                      />
                      <span className="text-sm text-secondary">
                        Enable team event emission for debugging and monitoring
                      </span>
                    </div>
                  </label>
                </div>
              )}

              <div className="space-y-2 mt-4">
                <h3 className="text-sm font-medium text-primary">
                  Termination Condition
                </h3>
                <div className="bg-secondary p-4 rounded-md">
                  {component.config.termination_condition ? (
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Timer className="w-4 h-4 text-secondary" />
                        <span className="text-sm">
                          {component.config.termination_condition.label ||
                            component.config.termination_condition
                              .component_type}
                        </span>
                      </div>
                      {onNavigate && (
                        <Button
                          type="text"
                          icon={<Edit className="w-4 h-4" />}
                          onClick={() =>
                            onNavigate(
                              "termination",
                              component.config.termination_condition?.label ||
                                "",
                              "termination_condition"
                            )
                          }
                        />
                      )}
                    </div>
                  ) : (
                    <div className="text-sm text-secondary text-center">
                      No termination condition configured
                    </div>
                  )}
                </div>
              </div>
            </div>
          ),
        },
      ]}
    />
  );
};

export default React.memo(TeamFields);
