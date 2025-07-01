import React from "react";
import { Button, Form, Input, InputNumber } from "antd";

import {
  Component,
  ComponentConfig,
  FunctionToolConfig,
} from "../../../../../types/datamodel";
import {
  isTeamComponent,
  isAgentComponent,
  isModelComponent,
  isToolComponent,
  isTerminationComponent,
  isWorkbenchComponent,
} from "../../../../../types/guards";
import DetailGroup from "../detailgroup";
import { TeamFields } from "./team-fields";
import { AgentFields } from "./agent-fields";
import { ModelFields } from "./model-fields";
import { ToolFields } from "./tool-fields";
import { TerminationFields } from "./termination-fields";
import { WorkbenchFields } from "./workbench";
import { Edit, MinusCircle, PlusCircle } from "lucide-react";
import { EditPath } from "../component-editor";

const { TextArea } = Input;

export interface NodeEditorFieldsProps {
  component: Component<ComponentConfig>;
  onNavigate: (componentType: string, id: string, parentField: string) => void;
  workingCopy: Component<ComponentConfig> | null;
  setWorkingCopy: (component: Component<ComponentConfig> | null) => void;
  editPath: EditPath[];
  updateComponentAtPath: (
    root: Component<ComponentConfig>,
    path: EditPath[],
    updates: Partial<Component<ComponentConfig>>
  ) => Component<ComponentConfig>;
  getCurrentComponent: (
    root: Component<ComponentConfig>
  ) => Component<ComponentConfig> | null;
}

const NodeEditorFields: React.FC<NodeEditorFieldsProps> = ({
  component,
  onNavigate,
  workingCopy,
  setWorkingCopy,
  editPath,
  updateComponentAtPath,
  getCurrentComponent,
}) => {
  let specificFields = null;

  if (isTeamComponent(component)) {
    specificFields = (
      <DetailGroup title="Configuration">
        <TeamFields
          component={component}
          onNavigate={onNavigate}
          onChange={(updates) => {
            if (
              workingCopy &&
              setWorkingCopy &&
              editPath &&
              updateComponentAtPath
            ) {
              const updatedCopy = updateComponentAtPath(
                workingCopy,
                editPath,
                updates
              );
              setWorkingCopy(updatedCopy);
            }
          }}
          // onChange={onChange}
          // workingCopy={workingCopy}
          // setWorkingCopy={setWorkingCopy}
          // editPath={editPath}
          // updateComponentAtPath={updateComponentAtPath}
          // getCurrentComponent={getCurrentComponent}
        />
      </DetailGroup>
    );
  } else if (isAgentComponent(component)) {
    specificFields = (
      <DetailGroup title="Configuration">
        <AgentFields
          component={component}
          onChange={(updates) => {
            if (
              workingCopy &&
              setWorkingCopy &&
              editPath &&
              updateComponentAtPath
            ) {
              const updatedCopy = updateComponentAtPath(
                workingCopy,
                editPath,
                updates
              );
              setWorkingCopy(updatedCopy);
            }
          }}
          onNavigate={onNavigate}
          workingCopy={workingCopy}
          setWorkingCopy={setWorkingCopy}
          editPath={editPath}
          updateComponentAtPath={updateComponentAtPath}
          getCurrentComponent={getCurrentComponent}
        />
      </DetailGroup>
    );
  } else if (isModelComponent(component)) {
    specificFields = (
      <DetailGroup title="Configuration">
        <ModelFields
          component={component}
          onChange={(updates) => {
            if (
              workingCopy &&
              setWorkingCopy &&
              editPath &&
              updateComponentAtPath
            ) {
              const updatedCopy = updateComponentAtPath(
                workingCopy,
                editPath,
                updates
              );
              setWorkingCopy(updatedCopy);
            }
          }}
        />
      </DetailGroup>
    );
  } else if (isWorkbenchComponent(component)) {
    specificFields = (
      <DetailGroup title="Workbench Configuration">
        <WorkbenchFields
          component={component}
          onChange={(updates) => {
            if (
              workingCopy &&
              setWorkingCopy &&
              editPath &&
              updateComponentAtPath
            ) {
              const updatedCopy = updateComponentAtPath(
                workingCopy,
                editPath,
                updates
              );
              setWorkingCopy(updatedCopy);
            }
          }}
        />
      </DetailGroup>
    );
  }
  //  NOTE: Individual tools are deprecated - use workbenches instead
  //  This is kept for backward compatibility during migration
  //  else if (isToolComponent(component)) {
  //   specificFields = (
  //     <DetailGroup title="Configuration">
  //       <ToolFields
  //         component={component}
  //         onChange={(updates) => {
  //           if (
  //             workingCopy &&
  //             setWorkingCopy &&
  //             editPath &&
  //             updateComponentAtPath
  //           ) {
  //             const updatedCopy = updateComponentAtPath(
  //               workingCopy,
  //               editPath,
  //               updates
  //             );
  //             setWorkingCopy(updatedCopy);
  //           }
  //         }}
  //       />
  //     </DetailGroup>
  //   );
  // }
  else if (isTerminationComponent(component)) {
    specificFields = (
      <DetailGroup title="Configuration">
        <TerminationFields
          component={component}
          onChange={(updates) => {
            if (
              workingCopy &&
              setWorkingCopy &&
              editPath &&
              updateComponentAtPath
            ) {
              const updatedCopy = updateComponentAtPath(
                workingCopy,
                editPath,
                updates
              );
              setWorkingCopy(updatedCopy);
            }
          }}
          onNavigate={onNavigate}
        />
      </DetailGroup>
    );
  } else if (isWorkbenchComponent(component)) {
    specificFields = (
      <DetailGroup title="Configuration">
        <WorkbenchFields
          component={component}
          onChange={(updates) => {
            if (
              workingCopy &&
              setWorkingCopy &&
              editPath &&
              updateComponentAtPath
            ) {
              const updatedCopy = updateComponentAtPath(
                workingCopy,
                editPath,
                updates
              );
              setWorkingCopy(updatedCopy);
            }
          }}
        />
      </DetailGroup>
    );
  }

  return (
    <>
      <DetailGroup title="Component Details">
        <CommonFields />
      </DetailGroup>
      {specificFields}
    </>
  );
};

export default NodeEditorFields;

// // fields/common-fields.tsx

export const CommonFields: React.FC = () => {
  return (
    <>
      <Form.Item label="Label" name="label">
        <Input />
      </Form.Item>
      <Form.Item label="Description" name="description">
        <TextArea rows={4} />
      </Form.Item>
      <div className="grid grid-cols-2 gap-4">
        <Form.Item label="Version" name="version">
          <InputNumber
            min={1}
            precision={0}
            className="w-full"
            placeholder="e.g., 1"
          />
        </Form.Item>
        <Form.Item label="Component Version" name="component_version">
          <InputNumber
            min={1}
            precision={0}
            className="w-full"
            placeholder="e.g., 1"
          />
        </Form.Item>
      </div>
    </>
  );
};

interface NestedComponentButtonProps {
  label: string;
  component: Component<ComponentConfig> | Component<ComponentConfig>[];
  parentField: string;
  onNavigate: (componentType: string, id: string, parentField: string) => void;
  workingCopy?: Component<ComponentConfig> | null;
  setWorkingCopy?: (component: Component<ComponentConfig> | null) => void;
  editPath?: any[];
  updateComponentAtPath?: any;
  getCurrentComponent?: any;
}

export const NestedComponentButton: React.FC<NestedComponentButtonProps> = ({
  label,
  component,
  parentField,
  onNavigate,
  workingCopy,
  setWorkingCopy,
  editPath,
  updateComponentAtPath,
  getCurrentComponent,
}) => {
  if (Array.isArray(component)) {
    return (
      <div className="space-y-2 mb-4">
        <div className="flex justify-between items-center">
          <span className="text-sm font-medium">{label}</span>
          {parentField === "tools" && (
            <Button
              type="dashed"
              size="small"
              onClick={() => {
                const blankTool: Component<FunctionToolConfig> = {
                  provider: "autogen_core.tools.FunctionTool",
                  component_type: "tool",
                  version: 1,
                  component_version: 1,
                  description:
                    "Create custom tools by wrapping standard Python functions.",
                  label: "New Tool",
                  config: {
                    source_code: "def new_function():\n    pass",
                    name: "new_function",
                    description: "Description of the new function",
                    global_imports: [],
                    has_cancellation_support: false,
                  },
                };

                if (
                  workingCopy &&
                  setWorkingCopy &&
                  updateComponentAtPath &&
                  getCurrentComponent &&
                  editPath
                ) {
                  const currentTools =
                    component as Component<ComponentConfig>[];
                  const updatedTools = [...currentTools, blankTool];
                  const updatedCopy = updateComponentAtPath(
                    workingCopy,
                    editPath,
                    {
                      config: {
                        ...getCurrentComponent(workingCopy)?.config,
                        tools: updatedTools,
                      },
                    }
                  );
                  setWorkingCopy(updatedCopy);
                }
              }}
              icon={<PlusCircle className="w-4 h-4" />}
            >
              Add Tool
            </Button>
          )}
        </div>
        {component.map((item, index) => (
          <div key={item.label} className="flex items-center gap-2">
            <Button
              onClick={() =>
                onNavigate(item.component_type, item.label || "", parentField)
              }
              className="w-full flex justify-between items-center"
            >
              <span>{item.label}</span>
              <Edit className="w-4 h-4" />
            </Button>
            {parentField === "tools" && (
              <Button
                type="text"
                danger
                icon={<MinusCircle className="w-4 h-4" />}
                onClick={() => {
                  if (
                    workingCopy &&
                    setWorkingCopy &&
                    updateComponentAtPath &&
                    getCurrentComponent &&
                    editPath
                  ) {
                    const currentTools =
                      component as Component<ComponentConfig>[];
                    const updatedTools = currentTools.filter(
                      (_, idx) => idx !== index
                    );
                    const updatedCopy = updateComponentAtPath(
                      workingCopy,
                      editPath,
                      {
                        config: {
                          ...getCurrentComponent(workingCopy)?.config,
                          tools: updatedTools,
                        },
                      }
                    );
                    setWorkingCopy(updatedCopy);
                  }
                }}
              />
            )}
          </div>
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
