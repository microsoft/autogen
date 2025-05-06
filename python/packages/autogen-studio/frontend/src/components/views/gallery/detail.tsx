import React, { useState, useEffect } from "react";
import { Tabs, Button, Tooltip, Drawer, Input } from "antd";
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
} from "lucide-react";
import { ComponentEditor } from "../teambuilder/builder/component-editor/component-editor";
import { TruncatableText } from "../atoms";
import {
  Component,
  ComponentConfig,
  ComponentTypes,
  Gallery,
} from "../../types/datamodel";
import TextArea from "antd/es/input/TextArea";

type CategoryKey = `${ComponentTypes}s`;

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
  }
> = ({ item, onEdit, onDuplicate, onDelete, index, allowDelete }) => (
  <div
    className="bg-secondary rounded overflow-hidden group h-full cursor-pointer"
    onClick={() => onEdit(item, index)}
  >
    <div className="px-4 py-3 flex items-center justify-between border-b border-tertiary">
      <div className="text-xs text-secondary truncate flex-1">
        {item.provider}
      </div>
      <div className="flex gap-0">
        {allowDelete && (
          <Button
            title="Delete"
            type="text"
            className="h-6 w-6 flex items-center justify-center p-0 opacity-0 group-hover:opacity-100 transition-opacity text-red-500 hover:text-red-600"
            icon={<Trash className="w-3.5 h-3.5" />}
            onClick={(e) => {
              e.stopPropagation();
              onDelete(item, index);
            }}
          />
        )}
        <Button
          title="Duplicate"
          type="text"
          className="h-6 w-6 flex items-center justify-center p-0 opacity-0 group-hover:opacity-100 transition-opacity"
          icon={<Copy className="w-3.5 h-3.5" />}
          onClick={(e) => {
            e.stopPropagation();
            onDuplicate(item, index);
          }}
        />
        <Button
          title="Edit"
          type="text"
          className="h-6 w-6 flex items-center justify-center p-0 opacity-0 group-hover:opacity-100 transition-opacity"
          icon={<Edit className="w-3.5 h-3.5" />}
          onClick={(e) => {
            e.stopPropagation();
            onEdit(item, index);
          }}
        />
      </div>
    </div>
    <div className="p-4 pb-0 pt-3">
      <div className="text-base font-medium mb-2">{item.label}</div>
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
  } & CardActions
> = ({ items, title, ...actions }) => (
  <div>
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 auto-rows-fr">
      {items.map((item, idx) => (
        <ComponentCard
          key={idx}
          item={item}
          index={idx}
          allowDelete={items.length > 1}
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
} as const;

// Add default configurations for each component type
const defaultConfigs: Record<ComponentTypes, ComponentConfig> = {
  team: { selector_prompt: "Default selector prompt", participants: [] } as any,
  agent: { name: "New Agent", description: "" } as any,
  model: { model: "gpt-3.5", api_key: "" } as any,
  tool: {
    source_code: "",
    name: "New Tool",
    description: "A new tool",
    global_imports: [],
    has_cancellation_support: false,
  },
  termination: { max_messages: 1 },
};

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
  const [tempName, setTempName] = useState(gallery.config.name);
  const [tempDescription, setTempDescription] = useState(
    gallery.config.metadata.description
  );

  useEffect(() => {
    setTempName(gallery.config.name);
    setTempDescription(gallery.config.metadata.description);
    setActiveTab("team");
    setEditingComponent(null);
  }, [gallery.id]);

  const updateGallery = (
    category: CategoryKey,
    updater: (
      components: Component<ComponentConfig>[]
    ) => Component<ComponentConfig>[]
  ) => {
    const updatedGallery = {
      ...gallery,
      config: {
        ...gallery.config,
        components: {
          ...gallery.config.components,
          [category]: updater(gallery.config.components[category]),
        },
      },
    };
    onSave(updatedGallery);
    onDirtyStateChange(true);
  };

  const handlers = {
    onEdit: (component: Component<ComponentConfig>, index: number) => {
      setEditingComponent({
        component,
        category: `${activeTab}s` as CategoryKey,
        index,
      });
    },

    onDuplicate: (component: Component<ComponentConfig>, index: number) => {
      const category = `${activeTab}s` as CategoryKey;
      const baseLabel = component.label?.replace(/_\d+$/, "");
      const components = gallery.config.components[category];

      const nextNumber =
        Math.max(
          ...components
            .map((c) => {
              const match = c.label?.match(
                new RegExp(`^${baseLabel}_?(\\d+)?$`)
              );
              return match ? parseInt(match[1] || "0") : 0;
            })
            .filter((n) => !isNaN(n)),
          0
        ) + 1;

      updateGallery(category, (components) => [
        ...components,
        { ...component, label: `${baseLabel}_${nextNumber}` },
      ]);
    },

    onDelete: (component: Component<ComponentConfig>, index: number) => {
      const category = `${activeTab}s` as CategoryKey;
      updateGallery(category, (components) =>
        components.filter((_, i) => i !== index)
      );
    },
  };

  const handleAdd = () => {
    const category = `${activeTab}s` as CategoryKey;
    const components = gallery.config.components[category];
    let newComponent: Component<ComponentConfig>;
    const newLabel = `New ${
      activeTab.charAt(0).toUpperCase() + activeTab.slice(1)
    }`;

    if (components.length > 0) {
      // Clone the entire component and just modify the label
      newComponent = {
        ...components[0], // This preserves all fields (provider, version, description, etc.)
        label: newLabel,
      };
    } else {
      // Only for empty categories, use default config
      newComponent = {
        provider: "new",
        component_type: activeTab,
        config: defaultConfigs[activeTab],
        label: newLabel,
      };
    }

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

  const tabItems = Object.entries(iconMap).map(([key, Icon]) => {
    // Determine display names
    const singular =
      key === "team"
        ? "Workflow"
        : key.charAt(0).toUpperCase() + key.slice(1);
    const plural =
      key === "team"
        ? "Workflows"
        : singular + "s";
  
    // Count items in this category
    const count = gallery.config.components[
      `${key}s` as CategoryKey
    ].length;
  
    return {
      key,
      label: (
        <span className="flex items-center gap-2">
          <Icon className="w-5 h-5" />
          {plural}
          <span className="text-xs font-light text-secondary">
            ({count})
          </span>
        </span>
      ),
      children: (
        <div>
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-base font-medium">
              {count} {count === 1 ? singular : plural}
            </h3>
            <Button
              type="primary"
              icon={<Plus className="w-4 h-4" />}
              onClick={() => {
                setActiveTab(key as ComponentTypes);
                handleAdd();
              }}
            >
              {`Add ${singular}`}
            </Button>
          </div>
          <ComponentGrid
            items={gallery.config.components[`${key}s` as CategoryKey]}
            title={key}
            {...handlers}
          />
        </div>
      ),
    };
  });

  return (
    <div className="max-w-7xl mx-auto px-4">
      <div className="relative h-64 rounded bg-secondary overflow-hidden mb-8">
        <img
          src="/images/bg/layeredbg.svg"
          alt="Collection Banner"
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
                    {gallery.config.name}
                  </h1>
                )}
                {gallery.config.url && (
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
                  {gallery.config.metadata.description}
                </p>
                <div className="flex gap-0">
                  <Tooltip title="Edit Gallery">
                    <Button
                      icon={<Edit className="w-4 h-4" />}
                      onClick={() => setIsEditingDetails(true)}
                      type="text"
                      className="text-white hover:text-white/80"
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
                {Object.values(gallery.config.components).reduce(
                  (sum, arr) => sum + arr.length,
                  0
                )}{" "}
                components
              </span>
            </div>
            <div className="bg-tertiary backdrop-blur rounded p-2 text-sm">
              v{gallery.config.metadata.version}
            </div>
          </div>
        </div>
      </div>

      <Tabs
        items={tabItems}
        className="gallery-tabs"
        size="large"
        onChange={(key) => setActiveTab(key as ComponentTypes)}
      />

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
