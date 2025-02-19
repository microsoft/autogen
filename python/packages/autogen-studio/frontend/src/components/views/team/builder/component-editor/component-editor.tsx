import React, { useState, useCallback } from "react";
import { Button, Breadcrumb } from "antd";
import { ChevronLeft } from "lucide-react";
import { Component, ComponentConfig } from "../../../../types/datamodel";
import {
  isTeamComponent,
  isAgentComponent,
  isModelComponent,
  isToolComponent,
  isTerminationComponent,
} from "../../../../types/guards";
import { AgentFields } from "./fields/agent-fields";
import { ModelFields } from "./fields/model-fields";
import { TeamFields } from "./fields/team-fields";
import { ToolFields } from "./fields/tool-fields";
import { TerminationFields } from "./fields/termination-fields";

export interface EditPath {
  componentType: string;
  id: string;
  parentField: string;
}

export interface ComponentEditorProps {
  component: Component<ComponentConfig>;
  onChange: (updatedComponent: Component<ComponentConfig>) => void;
  onClose?: () => void;
  navigationDepth?: boolean;
}

export const ComponentEditor: React.FC<ComponentEditorProps> = ({
  component,
  onChange,
  onClose,
  navigationDepth = false,
}) => {
  // const workingCopy = Object.assign({}, component);
  const [editPath, setEditPath] = useState<EditPath[]>([]);
  const [workingCopy, setWorkingCopy] = useState<Component<ComponentConfig>>(
    Object.assign({}, component)
  );

  // Reset working copy when component changes
  React.useEffect(() => {
    setWorkingCopy(component);
    setEditPath([]);
  }, [component]);

  const getCurrentComponent = useCallback(
    (root: Component<ComponentConfig>) => {
      return editPath.reduce<Component<ComponentConfig> | null>(
        (current, path) => {
          if (!current) return null;

          const field = current.config[
            path.parentField as keyof typeof current.config
          ] as
            | Component<ComponentConfig>[]
            | Component<ComponentConfig>
            | undefined;

          if (Array.isArray(field)) {
            return (
              field.find(
                (item) =>
                  item.label === path.id ||
                  (item.config &&
                    "name" in item.config &&
                    item.config.name === path.id)
              ) || null
            );
          }

          return field || null;
        },
        root
      );
    },
    [editPath]
  );

  const updateComponentAtPath = useCallback(
    (
      root: Component<ComponentConfig>,
      path: EditPath[],
      updates: Partial<Component<ComponentConfig>>
    ): Component<ComponentConfig> => {
      if (path.length === 0) {
        return {
          ...root,
          ...updates,
          config: {
            ...root.config,
            ...(updates.config || {}),
          },
        };
      }

      const [currentPath, ...remainingPath] = path;
      const field =
        root.config[currentPath.parentField as keyof typeof root.config];

      const updateField = (fieldValue: any): any => {
        if (Array.isArray(fieldValue)) {
          return fieldValue.map((item) => {
            if (!("component_type" in item)) return item;
            if (
              item.label === currentPath.id ||
              ("name" in item.config && item.config.name === currentPath.id)
            ) {
              return updateComponentAtPath(item, remainingPath, updates);
            }
            return item;
          });
        }

        if (fieldValue && "component_type" in fieldValue) {
          return updateComponentAtPath(
            fieldValue as Component<ComponentConfig>,
            remainingPath,
            updates
          );
        }

        return fieldValue;
      };

      return {
        ...root,
        config: {
          ...root.config,
          [currentPath.parentField]: updateField(field),
        },
      };
    },
    []
  );

  const handleComponentUpdate = useCallback(
    (updates: Partial<Component<ComponentConfig>>) => {
      const updatedComponent = updateComponentAtPath(
        workingCopy,
        editPath,
        updates
      );
      console.log("updatedComponent", updatedComponent);
      setWorkingCopy(updatedComponent);
      //   onChange(updatedComponent);
    },
    [workingCopy, editPath, updateComponentAtPath]
  );

  const handleNavigate = useCallback(
    (componentType: string, id: string, parentField: string) => {
      if (!navigationDepth) return;
      setEditPath((prev) => [...prev, { componentType, id, parentField }]);
    },
    [navigationDepth]
  );

  const handleNavigateBack = useCallback(() => {
    setEditPath((prev) => prev.slice(0, -1));
  }, []);

  const currentComponent = getCurrentComponent(workingCopy) || workingCopy;

  const renderFields = useCallback(() => {
    const commonProps = {
      component: currentComponent,
      onChange: handleComponentUpdate,
    };

    if (isTeamComponent(currentComponent)) {
      return (
        <TeamFields
          component={currentComponent}
          onChange={handleComponentUpdate}
          onNavigate={handleNavigate}
        />
      );
    }
    if (isAgentComponent(currentComponent)) {
      return (
        <AgentFields
          component={currentComponent}
          onChange={handleComponentUpdate}
          onNavigate={handleNavigate}
        />
      );
    }
    if (isModelComponent(currentComponent)) {
      return (
        <ModelFields
          component={currentComponent}
          onChange={handleComponentUpdate}
        />
      );
    }
    if (isToolComponent(currentComponent)) {
      return <ToolFields {...commonProps} />;
    }
    if (isTerminationComponent(currentComponent)) {
      return (
        <TerminationFields
          component={currentComponent}
          onChange={handleComponentUpdate}
        />
      );
    }

    return null;
  }, [currentComponent, handleComponentUpdate, handleNavigate]);

  const breadcrumbItems = React.useMemo(
    () => [
      { title: workingCopy.label || "Root" },
      ...editPath.map((path) => ({
        title: path.id,
      })),
    ],
    [workingCopy.label, editPath]
  );

  const handleSave = useCallback(() => {
    console.log("working copy", workingCopy.config);
    onChange(workingCopy);
    onClose?.();
  }, [workingCopy, onChange, onClose]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-4 mb-6">
        {navigationDepth && editPath.length > 0 && (
          <Button
            onClick={handleNavigateBack}
            icon={<ChevronLeft className="w-4 h-4" />}
            type="text"
          />
        )}
        <div className="flex-1">
          <Breadcrumb items={breadcrumbItems} />
        </div>
      </div>
      <div className="flex-1 overflow-y-auto">{renderFields()}</div>
      {onClose && (
        <div className="flex justify-end gap-2 mt-6 pt-4 border-t border-secondary">
          <Button onClick={onClose}>Cancel</Button>
          <Button type="primary" onClick={handleSave}>
            Save Changes
          </Button>
        </div>
      )}
    </div>
  );
};

export default ComponentEditor;
