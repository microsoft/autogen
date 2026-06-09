import React, { useState, useEffect, useCallback, useRef } from "react";
import {
  Tabs,
  Button,
  Tooltip,
  Drawer,
  Input,
  message,
  Dropdown,
  Tag,
} from "antd";
import {
  Package,
  Users,
  Bot,
  Globe,
  Wrench,
  Brain,
  Timer,
  Edit,
  Copy,
  Trash,
  Plus,
  Download,
  Briefcase,
  Code,
  FormInput,
  ChevronDown,
  Server,
} from "lucide-react";
import { ComponentEditor } from "../teambuilder/builder/component-editor/component-editor";
import { MonacoEditor } from "../monaco";
import { TruncatableText } from "../atoms";
import {
  Component,
  ComponentConfig,
  ComponentTypes,
  Gallery,
} from "../../types/datamodel";
import {
  getTemplatesForDropdown,
  createComponentFromTemplateById,
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
} from "../../types/component-templates";
import { isMcpWorkbench } from "../../types/guards";
import TextArea from "antd/es/input/TextArea";
import Icon from "../../icons";
import { AddComponentDropdown } from "../../shared";

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

interface CardActions {
  onEdit: (component: Component<ComponentConfig>, index: number) => void;
  onDuplicate: (component: Component<ComponentConfig>, index: number) => void;
  onDelete: (component: Component<ComponentConfig>, index: number) => void;
}

// Component Card
const ComponentCard: React.FC<
  CardActions & {
    item: Component<ComponentConfig>;
    index: number;
    allowDelete: boolean;
    disabled?: boolean;
  }
> = ({
  item,
  onEdit,
  onDuplicate,
  onDelete,
  index,
  allowDelete,
  disabled = false,
}) => (
  <div
    className={`bg-secondary rounded overflow-hidden group h-full ${
      disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"
    }`}
    onClick={() => !disabled && onEdit(item, index)}
  >
    <div className="px-4 py-3 flex items-center justify-between border-b border-tertiary">
      <div className="text-xs text-secondary truncate flex-1">
        {item.label || "Unnamed Component"}
      </div>
      <div className="flex gap-0">
        {allowDelete && (
          <Button
            title="Delete"
            type="text"
            className="h-6 w-6 flex items-center justify-center p-0 opacity-0 group-hover:opacity-100 transition-opacity text-red-500 hover:text-red-600"
            icon={<Trash className="w-3.5 h-3.5" />}
            disabled={disabled}
            onClick={(e) => {
              e.stopPropagation();
              if (!disabled) onDelete(item, index);
            }}
          />
        )}
        <Button
          title="Duplicate"
          type="text"
          className="h-6 w-6 flex items-center justify-center p-0 opacity-0 group-hover:opacity-100 transition-opacity"
          icon={<Copy className="w-3.5 h-3.5" />}
          disabled={disabled}
          onClick={(e) => {
            e.stopPropagation();
            if (!disabled) onDuplicate(item, index);
          }}
        />
        <Button
          title="Edit"
          type="text"
          className="h-6 w-6 flex items-center justify-center p-0 opacity-0 group-hover:opacity-100 transition-opacity"
          icon={<Edit className="w-3.5 h-3.5" />}
          disabled={disabled}
          onClick={(e) => {
            e.stopPropagation();
            if (!disabled) onEdit(item, index);
          }}
        />
      </div>
    </div>
    <div className="p-4 pb-0 pt-3">
      <div className="text-base font-medium mb-2 flex items-center gap-2">
        {item.component_type === "workbench" && isMcpWorkbench(item) && (
          <Icon icon="mcp" size={6} className="inline-block" />
        )}{" "}
        <span className="line-clamp-1">
          {item.label || "Unnamed Component"}
        </span>
      </div>
      <div className="text-xs text-secondary truncate mb-2">
        {item.provider}
      </div>
      <div className="text-sm text-secondary line-clamp-2 mb-3 min-h-[40px]">
        <TruncatableText
          content={item.description || ""}
          showFullscreen={false}
          textThreshold={70}
        />
      </div>
    </div>
  </div>
);

// Component Grid
const ComponentGrid: React.FC<
  {
    items: Component<ComponentConfig>[];
    title: string;
    disabled?: boolean;
  } & CardActions
> = ({ items, title, disabled = false, ...actions }) => (
  <div>
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 auto-rows-fr">
      {items.map((item, idx) => (
        <ComponentCard
          key={idx}
          item={item}
          index={idx}
          allowDelete={items.length > 1}
          disabled={disabled}
          {...actions}
        />
      ))}
    </div>
  </div>
);

const iconMap = {
  team: Users,
  agent: Bot,
  tool: Wrench,
  model: Brain,
  termination: Timer,
  workbench: Briefcase,
} as const;

export const GalleryDetail: React.FC<{
  gallery: Gallery;
  onSave: (updates: Partial<Gallery>) => void;
  onDirtyStateChange: (isDirty: boolean) => void;
}> = ({ gallery, onSave, onDirtyStateChange }) => {
  if (!gallery.config.components) {
    return <div className="text-secondary">No components found</div>;
  }
  const [editingComponent, setEditingComponent] = useState<{
    component: Component<ComponentConfig>;
    category: CategoryKey;
    index: number;
  } | null>(null);
  const [activeTab, setActiveTab] = useState<ComponentTypes>("team");
  const [isEditingDetails, setIsEditingDetails] = useState(false);
  const [isJsonEditing, setIsJsonEditing] = useState(false);
  const [workingCopy, setWorkingCopy] = useState<Gallery>(gallery);
  const [jsonValue, setJsonValue] = useState<string>("");
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [isDirty, setIsDirty] = useState(false);
  const [tempName, setTempName] = useState(gallery.config.name);
  const [tempDescription, setTempDescription] = useState(
    gallery.config.metadata.description
  );

  const [messageApi, contextHolder] = message.useMessage();
  const editorRef = useRef(null);

  useEffect(() => {
    setTempName(gallery.config.name);
    setTempDescription(gallery.config.metadata.description);
    setWorkingCopy(gallery);
    setJsonValue(JSON.stringify(gallery, null, 2));
    setHasUnsavedChanges(false);
    setIsDirty(false);
    setActiveTab("team");
    setEditingComponent(null);
    setIsJsonEditing(false);
  }, [gallery.id]);

  const updateGallery = (
    category: CategoryKey,
    updater: (
      components: Component<ComponentConfig>[]
    ) => Component<ComponentConfig>[]
  ) => {
    const currentGallery = isJsonEditing ? workingCopy : gallery;
    const updatedGallery = {
      ...currentGallery,
      config: {
        ...currentGallery.config,
        components: {
          ...currentGallery.config.components,
          [category]: updater(currentGallery.config.components[category]),
        },
      },
    };

    if (isJsonEditing) {
      setWorkingCopy(updatedGallery);
    } else {
      onSave(updatedGallery);
      onDirtyStateChange(true);
    }
  };

  const handleJsonChange = (value: string) => {
    setJsonValue(value);
    setIsDirty(true);
  };

  const handlers = {
    onEdit: (component: Component<ComponentConfig>, index: number) => {
      setEditingComponent({
        component,
        category: getCategoryKey(activeTab),
        index,
      });
    },

    onDuplicate: (component: Component<ComponentConfig>, index: number) => {
      const category = getCategoryKey(activeTab);
      const baseLabel = component.label?.replace(/_\d+$/, "");
      const components = gallery.config.components[category] || [];

      const nextNumber =
        Math.max(
          ...components
            .map((c: Component<ComponentConfig>) => {
              const match = c.label?.match(
                new RegExp(`^${baseLabel}_?(\\d+)?$`)
              );
              return match ? parseInt(match[1] || "0") : 0;
            })
            .filter((n: number) => !isNaN(n)),
          0
        ) + 1;

      updateGallery(category, (components) => [
        ...components,
        { ...component, label: `${baseLabel}_${nextNumber}` },
      ]);
    },

    onDelete: (component: Component<ComponentConfig>, index: number) => {
      const category = getCategoryKey(activeTab);
      updateGallery(category, (components) =>
        components.filter((_, i) => i !== index)
      );
    },
  };

  // Handler for the reusable AddComponentDropdown
  const handleComponentAdded = (
    newComponent: Component<ComponentConfig>,
    category: CategoryKey
  ) => {
    updateGallery(category, (components) => {
      const newComponents = [...components, newComponent];
      setEditingComponent({
        component: newComponent,
        category,
        index: newComponents.length - 1,
      });
      return newComponents;
    });
  };

  const handleAddWorkbench = (templateId: string) => {
    const category = getCategoryKey("workbench");

    try {
      const newComponent = createWorkbenchFromTemplate(templateId);

      updateGallery(category, (components) => {
        const newComponents = [...components, newComponent];
        setEditingComponent({
          component: newComponent,
          category,
          index: newComponents.length - 1,
        });
        return newComponents;
      });
    } catch (error) {
      console.error("Error creating workbench from template:", error);
      messageApi.error("Failed to create workbench");
    }
  };

  const handleComponentUpdate = (
    updatedComponent: Component<ComponentConfig>
  ) => {
    if (!editingComponent) return;

    updateGallery(editingComponent.category, (components) =>
      components.map((c, i) =>
        i === editingComponent.index ? updatedComponent : c
      )
    );
    setEditingComponent(null);
  };

  const handleJsonSave = () => {
    try {
      const updatedGallery = JSON.parse(jsonValue);
      setWorkingCopy(updatedGallery);
      onSave(updatedGallery);
      onDirtyStateChange(true);
      setIsJsonEditing(false);
      setIsDirty(false);
      messageApi.success("Gallery updated successfully!");
    } catch (error) {
      messageApi.error("Invalid JSON format. Please check your syntax.");
      console.error("JSON parse error:", error);
    }
  };

  const handleDetailsSave = () => {
    const updatedGallery = {
      ...gallery,
      config: {
        ...gallery.config,
        name: tempName,
        metadata: {
          ...gallery.config.metadata,
          description: tempDescription,
        },
      },
    };
    onSave(updatedGallery);
    onDirtyStateChange(true);
    setIsEditingDetails(false);
  };

  const handleDownload = () => {
    const dataStr = JSON.stringify(gallery, null, 2);
    const dataBlob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${gallery.config.name
      .toLowerCase()
      .replace(/\s+/g, "_")}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const currentGallery = isJsonEditing ? workingCopy : gallery;

  const tabItems = Object.entries(iconMap).map(([key, Icon]) => ({
    key,
    label: (
      <span className="flex items-center gap-2">
        <Icon className="w-5 h-5" />
        {key.charAt(0).toUpperCase() + key.slice(1)}s
        <span className="text-xs font-light text-secondary">
          (
          {currentGallery.config.components[
            getCategoryKey(key as ComponentTypes)
          ]?.length || 0}
          )
        </span>
      </span>
    ),
    children: (
      <div>
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-base font-medium">
            {currentGallery.config.components[
              getCategoryKey(key as ComponentTypes)
            ]?.length || 0}{" "}
            {(currentGallery.config.components[
              getCategoryKey(key as ComponentTypes)
            ]?.length || 0) === 1
              ? key.charAt(0).toUpperCase() + key.slice(1)
              : key.charAt(0).toUpperCase() + key.slice(1) + "s"}
          </h3>
          <AddComponentDropdown
            componentType={key as ComponentTypes}
            gallery={currentGallery}
            onComponentAdded={handleComponentAdded}
            disabled={isJsonEditing}
          />
        </div>
        <ComponentGrid
          items={
            currentGallery.config.components[
              getCategoryKey(key as ComponentTypes)
            ] || []
          }
          title={key}
          disabled={isJsonEditing}
          {...handlers}
        />
      </div>
    ),
  }));

  return (
    <div className="max-w-7xl px-4">
      {contextHolder}

      <div className="relative h-64 rounded bg-secondary overflow-hidden mb-8">
        <img
          src="/images/bg/layeredbg.svg"
          alt="Gallery Banner"
          className="absolute w-full h-full object-cover"
        />
        <div className="relative z-10 p-6 h-full flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                {isEditingDetails ? (
                  <Input
                    value={tempName}
                    onChange={(e) => setTempName(e.target.value)}
                    className="text-2xl font-medium bg-background/50 backdrop-blur px-2 py-1 rounded w-[400px]"
                  />
                ) : (
                  <h1 className="text-2xl font-medium text-primary">
                    {currentGallery.config.name}
                  </h1>
                )}
                {currentGallery.config.url && (
                  <Tooltip title="Remote Gallery">
                    <Globe className="w-5 h-5 text-secondary" />
                  </Tooltip>
                )}
              </div>
            </div>
            {isEditingDetails ? (
              <TextArea
                value={tempDescription}
                onChange={(e) => setTempDescription(e.target.value)}
                className="w-1/2 bg-background/50 backdrop-blur px-2 py-1 rounded mt-2"
                rows={2}
              />
            ) : (
              <div className="flex flex-col gap-2">
                <p className="text-secondary w-1/2 mt-2 line-clamp-2">
                  {currentGallery.config.metadata.description}
                </p>
                <div className="flex gap-0">
                  <Tooltip title="Edit Gallery">
                    <Button
                      icon={<Edit className="w-4 h-4" />}
                      onClick={() => setIsEditingDetails(true)}
                      type="text"
                      className="text-white hover:text-white/80"
                      disabled={isJsonEditing}
                    />
                  </Tooltip>
                  <Tooltip title="Download Gallery">
                    <Button
                      icon={<Download className="w-4 h-4" />}
                      onClick={handleDownload}
                      type="text"
                      className="text-white hover:text-white/80"
                    />
                  </Tooltip>
                  <Tooltip
                    title={isJsonEditing ? "Form Editor" : "JSON Editor"}
                  >
                    <Button
                      icon={
                        isJsonEditing ? (
                          <FormInput className="w-4 h-4" />
                        ) : (
                          <Code className="w-4 h-4" />
                        )
                      }
                      onClick={() => {
                        const newJsonMode = !isJsonEditing;
                        setIsJsonEditing(newJsonMode);
                        if (newJsonMode) {
                          setJsonValue(JSON.stringify(currentGallery, null, 2));
                          setIsDirty(false);
                        }
                      }}
                      type="text"
                      className="text-white hover:text-white/80"
                    />
                  </Tooltip>
                </div>
              </div>
            )}
            {isEditingDetails && (
              <div className="flex gap-2 mt-2">
                <Button onClick={() => setIsEditingDetails(false)}>
                  Cancel
                </Button>
                <Button type="primary" onClick={handleDetailsSave}>
                  Save
                </Button>
              </div>
            )}
          </div>
          <div className="flex gap-2">
            <div className="bg-tertiary backdrop-blur rounded p-2 flex items-center gap-2">
              <Package className="w-4 h-4 text-secondary" />
              <span className="text-sm">
                {Object.values(currentGallery.config.components).reduce(
                  (sum, arr) => sum + arr.length,
                  0
                )}{" "}
                components
              </span>
            </div>
            <div className="bg-tertiary backdrop-blur rounded p-2 text-sm">
              v{currentGallery.config.metadata.version}
            </div>
          </div>
        </div>
      </div>

      {isJsonEditing ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-medium">JSON Editor</h2>
              {isDirty && (
                <span className="text-orange-500 text-sm">
                  • Unsaved changes
                </span>
              )}
            </div>
            <div className="flex gap-2">
              <Button
                onClick={() => {
                  setIsJsonEditing(false);
                  setIsDirty(false);
                  setJsonValue(JSON.stringify(gallery, null, 2));
                }}
              >
                Cancel
              </Button>
              <Button type="primary" onClick={handleJsonSave}>
                Save Changes
              </Button>
            </div>
          </div>
          <div className="h-[600px] border border-secondary rounded">
            <MonacoEditor
              editorRef={editorRef}
              value={jsonValue}
              onChange={handleJsonChange}
              language="json"
              minimap={true}
            />
          </div>
        </div>
      ) : (
        <Tabs
          items={tabItems}
          className="gallery-tabs"
          size="large"
          onChange={(key) => setActiveTab(key as ComponentTypes)}
        />
      )}

      <Drawer
        title="Edit Component"
        placement="right"
        size="large"
        onClose={() => setEditingComponent(null)}
        open={!!editingComponent}
        className="component-editor-drawer"
      >
        {editingComponent && (
          <ComponentEditor
            component={editingComponent.component}
            onChange={handleComponentUpdate}
            onClose={() => setEditingComponent(null)}
            navigationDepth={true}
          />
        )}
      </Drawer>
    </div>
  );
};

export default GalleryDetail;
