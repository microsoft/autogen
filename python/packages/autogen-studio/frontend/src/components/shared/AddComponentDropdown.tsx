import React from "react";
import { Button, Dropdown, message } from "antd";
import { Plus, ChevronDown } from "lucide-react";
import {
  Component,
  ComponentConfig,
  ComponentTypes,
  Gallery,
} from "../types/datamodel";
import {
  getTeamTemplatesForDropdown,
  createTeamFromTemplate,
  getAgentTemplatesForDropdown,
  createAgentFromTemplate,
  getModelTemplatesForDropdown,
  createModelFromTemplate,
  getToolTemplatesForDropdown,
  createToolFromTemplate,
  getWorkbenchTemplatesForDropdown,
  createWorkbenchFromTemplate,
  getTerminationTemplatesForDropdown,
  createTerminationFromTemplate,
  type ComponentDropdownOption,
} from "../types/component-templates";

type CategoryKey =
  | "teams"
  | "agents"
  | "models"
  | "tools"
  | "workbenches"
  | "terminations";

// Helper function to get the correct category key for components
const getCategoryKey = (componentType: ComponentTypes): CategoryKey => {
  const mapping: Record<ComponentTypes, CategoryKey> = {
    team: "teams",
    agent: "agents",
    model: "models",
    tool: "tools",
    workbench: "workbenches",
    termination: "terminations",
  };
  return mapping[componentType];
};

interface AddComponentDropdownProps {
  componentType: ComponentTypes;
  gallery: Gallery;
  onComponentAdded: (
    component: Component<ComponentConfig>,
    category: CategoryKey
  ) => void;
  disabled?: boolean;
  showIcon?: boolean;
  showChevron?: boolean;
  size?: "small" | "middle" | "large";
  type?: "default" | "primary" | "dashed" | "link" | "text";
  className?: string;
  buttonText?: string;
  // Optional filter for specific component types (useful for MCP workbenches)
  templateFilter?: (template: ComponentDropdownOption) => boolean;
}

export const AddComponentDropdown: React.FC<AddComponentDropdownProps> = ({
  componentType,
  gallery,
  onComponentAdded,
  disabled = false,
  showIcon = true,
  showChevron = true,
  size = "middle",
  type = "primary",
  className = "",
  buttonText,
  templateFilter,
}) => {
  const [messageApi, contextHolder] = message.useMessage();

  // Helper function to get dropdown templates for each component type
  const getDropdownTemplatesForType = (
    componentType: ComponentTypes
  ): ComponentDropdownOption[] => {
    let templates: ComponentDropdownOption[] = [];

    switch (componentType) {
      case "team":
        templates = getTeamTemplatesForDropdown();
        break;
      case "agent":
        templates = getAgentTemplatesForDropdown();
        break;
      case "model":
        templates = getModelTemplatesForDropdown();
        break;
      case "tool":
        templates = getToolTemplatesForDropdown();
        break;
      case "workbench":
        templates = getWorkbenchTemplatesForDropdown();
        break;
      case "termination":
        templates = getTerminationTemplatesForDropdown();
        break;
      default:
        templates = [];
    }

    // Apply filter if provided
    if (templateFilter) {
      templates = templates.filter(templateFilter);
    }

    return templates;
  };

  // Generic handler for all component types
  const handleAddComponentFromTemplate = (
    componentType: ComponentTypes,
    templateId: string
  ) => {
    const category = getCategoryKey(componentType);

    try {
      let newComponent: Component<ComponentConfig>;

      switch (componentType) {
        case "team":
          newComponent = createTeamFromTemplate(templateId);
          break;
        case "agent":
          newComponent = createAgentFromTemplate(templateId);
          break;
        case "model":
          newComponent = createModelFromTemplate(templateId);
          break;
        case "tool":
          newComponent = createToolFromTemplate(templateId);
          break;
        case "workbench":
          newComponent = createWorkbenchFromTemplate(templateId);
          break;
        case "termination":
          newComponent = createTerminationFromTemplate(templateId);
          break;
        default:
          throw new Error(`Unsupported component type: ${componentType}`);
      }

      onComponentAdded(newComponent, category);
    } catch (error) {
      console.error(`Error creating ${componentType} from template:`, error);
      messageApi.error(`Failed to create ${componentType}`);
    }
  };

  const templates = getDropdownTemplatesForType(componentType);

  // Don't render if no templates available
  if (templates.length === 0) {
    return null;
  }

  const displayButtonText =
    buttonText ||
    `Add ${componentType.charAt(0).toUpperCase() + componentType.slice(1)}`;

  return (
    <>
      {contextHolder}
      <Dropdown
        menu={{
          items: templates.map((template) => ({
            key: template.key,
            label: (
              <div className="py-1">
                <div className="font-medium">{template.label}</div>
                <div className="text-xs text-secondary">
                  {template.description}
                </div>
              </div>
            ),
            onClick: () =>
              handleAddComponentFromTemplate(
                componentType,
                template.templateId
              ),
          })),
        }}
        trigger={["click"]}
        disabled={disabled}
      >
        <Button
          type={type}
          size={size}
          icon={showIcon ? <Plus className="w-4 h-4" /> : undefined}
          disabled={disabled}
          className={`flex items-center gap-1 ${className}`}
        >
          {displayButtonText}
          {showChevron && <ChevronDown className="w-3 h-3" />}
        </Button>
      </Dropdown>
    </>
  );
};

export default AddComponentDropdown;
