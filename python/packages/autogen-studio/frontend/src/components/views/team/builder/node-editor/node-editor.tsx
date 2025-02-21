import React from "react";
import { Form, Button, Drawer, Breadcrumb } from "antd";
import { ChevronLeft } from "lucide-react";
import { Component, ComponentConfig } from "../../../../types/datamodel";
import { NodeEditorProps } from "../types";
import { isComponent } from "../../../../types/guards";
import NodeEditorFields from "./fields/fields";

export interface EditPath {
  componentType: string;
  id: string;
  parentField: string;
}

export const NodeEditor: React.FC<
  NodeEditorProps & { onClose: () => void }
> = ({ node, onUpdate, onClose }) => {
  const [form] = Form.useForm();
  const [editPath, setEditPath] = React.useState<EditPath[]>([]);

  // Keep a working copy of the entire component structure
  const [workingCopy, setWorkingCopy] =
    React.useState<Component<ComponentConfig> | null>(
      node ? { ...node.data.component } : null
    );

  // Reset working copy when node changes
  React.useEffect(() => {
    if (node) {
      setWorkingCopy({ ...node.data.component });
      setEditPath([]);
    } else {
      setWorkingCopy(null);
    }
  }, [node]);

  // Initialize form values when edit path changes
  React.useEffect(() => {
    if (workingCopy) {
      const currentComponent = getCurrentComponent(workingCopy);
      if (currentComponent) {
        // Create form values object matching the field structure in NodeEditorFields
        const formValues = {
          label: currentComponent.label,
          description: currentComponent.description,
          // For each config field, create an array path ["config", "fieldname"]
          ...Object.entries(currentComponent.config).reduce(
            (acc, [key, value]) => {
              // Skip nested component fields as they're handled by buttons
              if (
                key !== "global_imports" &&
                typeof value === "object" &&
                (Array.isArray(value) || value?.component_type)
              ) {
                return acc;
              }
              return {
                ...acc,
                config: {
                  ...acc.config,
                  [key]: value,
                },
              };
            },
            { config: {} }
          ),
        };

        form.setFieldsValue(formValues);
      }
    }
  }, [workingCopy, form, editPath]);

  if (!node || !workingCopy) return null;

  const getCurrentComponent = (root: Component<ComponentConfig>) => {
    let current: Component<ComponentConfig> = root;

    for (const path of editPath) {
      const field = current.config[
        path.parentField as keyof typeof current.config
      ] as
        | Component<ComponentConfig>[]
        | Component<ComponentConfig>
        | undefined;

      if (Array.isArray(field)) {
        // For arrays, try to find the component by its label first, then by name
        const found = field.find(
          (item) =>
            item.label === path.id ||
            (item.config &&
              "name" in item.config &&
              item.config.name === path.id)
        );
        if (!found) return null;
        current = found;
      } else if (field) {
        // For single components, just use the field directly
        current = field;
      } else {
        return null;
      }
    }

    return current;
  };

  const updateComponentAtPath = <T extends ComponentConfig>(
    root: Component<T>,
    path: EditPath[],
    updates: Partial<Component<T>>
  ): Component<T> => {
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
    const result = { ...root };
    const field = result.config[currentPath.parentField as keyof T];
    const updatedConfig = { ...result.config } as T;

    if (Array.isArray(field)) {
      updatedConfig[currentPath.parentField as keyof T] = field.map((item) => {
        if (!isComponent(item)) return item;

        if (
          item.label === currentPath.id ||
          ("name" in item.config && item.config.name === currentPath.id)
        ) {
          return updateComponentAtPath(item, remainingPath, updates);
        }
        return item;
      }) as T[keyof T];
    } else if (field && isComponent(field)) {
      updatedConfig[currentPath.parentField as keyof T] = updateComponentAtPath(
        field,
        remainingPath,
        updates
      ) as T[keyof T];
    }

    return {
      ...result,
      config: updatedConfig,
    };
  };

  const navigateToComponent = (
    componentType: string,
    id: string,
    parentField: string
  ) => {
    console.log("Navigating to:", { componentType, id, parentField });

    // Update working copy with current form values before navigating
    const values = form.getFieldsValue();
    const updatedCopy = updateComponentAtPath(workingCopy, editPath, {
      label: values.label,
      description: values.description,
      config: {
        ...getCurrentComponent(workingCopy)?.config,
        ...values,
      },
    });
    setWorkingCopy(updatedCopy);

    // Navigate to new path
    const newPath = [...editPath, { componentType, id, parentField }];
    console.log("New edit path:", newPath);
    setEditPath(newPath);

    // Log the component we're going to
    const nextComponent = getCurrentComponent(updatedCopy);
    console.log("Next component:", nextComponent);
  };

  const navigateBack = () => {
    // Update working copy with current form values before navigating back
    const values = form.getFieldsValue();
    const updatedCopy = updateComponentAtPath(workingCopy, editPath, {
      label: values.label,
      description: values.description,
      config: values,
    });
    setWorkingCopy(updatedCopy);

    // Navigate back
    setEditPath(editPath.slice(0, -1));
  };

  const handleFormSubmit = async () => {
    try {
      const values = await form.validateFields();
      console.log("Form values on submit:", values);

      // Get the current component to preserve any nested components
      const currentComponent = getCurrentComponent(workingCopy);

      // Construct the updated component
      const updatedComponent = {
        ...currentComponent,
        label: values.label,
        description: values.description,
        config: {
          ...currentComponent?.config, // Preserve nested components
          ...values.config, // Update with new form values
        },
      };

      console.log("Updating component with:", updatedComponent);

      // Update working copy
      const finalCopy = updateComponentAtPath(
        workingCopy,
        editPath,
        updatedComponent
      );

      // Submit the entire working copy to parent
      onUpdate({
        ...node.data,
        component: finalCopy,
      });
    } catch (error) {
      console.error("Validation failed:", error);
    }
  };

  const getBreadcrumbItems = () => {
    return [
      { title: workingCopy.label || "Root" },
      ...editPath.map((path) => ({
        title: path.id,
      })),
    ];
  };

  const currentComponent = getCurrentComponent(workingCopy);

  return (
    <Drawer
      title={
        <div className="flex items-center gap-4">
          {" "}
          {editPath.length > 0 && (
            <Button
              onClick={navigateBack}
              icon={<ChevronLeft className="w-4 h-4" />}
              type="text"
            />
          )}
          <div className="flex-1">
            <Breadcrumb items={getBreadcrumbItems()} />
          </div>
        </div>
      }
      placement="right"
      size="large"
      onClose={onClose}
      open={true}
      className="node-editor-drawer"
    >
      <Form
        form={form}
        layout="vertical"
        className="h-full overflow-y-auto pb-16"
      >
        {currentComponent && (
          <NodeEditorFields
            component={currentComponent}
            onNavigate={navigateToComponent}
            editPath={editPath}
            workingCopy={workingCopy}
            setWorkingCopy={setWorkingCopy}
            updateComponentAtPath={updateComponentAtPath}
            getCurrentComponent={getCurrentComponent}
          />
        )}
        <div className="flex justify-end gap-2 mt-4 absolute bottom-0 right-0 left-0 p-4 bg-primary border-t">
          <Button onClick={onClose}>Cancel</Button>
          <Button type="primary" onClick={handleFormSubmit}>
            Save Changes
          </Button>
        </div>
      </Form>
    </Drawer>
  );
};

export default NodeEditor;
