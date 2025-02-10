import React from "react";
import { Input, Collapse, type CollapseProps } from "antd";
import { useDraggable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import {
  Brain,
  ChevronDown,
  Bot,
  Wrench,
  Timer,
  Maximize2,
  Minimize2,
  GripVertical,
} from "lucide-react";
import Sider from "antd/es/layout/Sider";
import { useGalleryStore } from "../../gallery/store";
import { ComponentTypes } from "../../../types/datamodel";

interface ComponentConfigTypes {
  [key: string]: any;
}

interface LibraryProps {}

interface PresetItemProps {
  id: string;
  type: ComponentTypes;
  config: ComponentConfigTypes;
  label: string;
  icon: React.ReactNode;
}

const PresetItem: React.FC<PresetItemProps> = ({
  id,
  type,
  config,
  label,
  icon,
}) => {
  const { attributes, listeners, setNodeRef, transform, isDragging } =
    useDraggable({
      id,
      data: {
        current: {
          type,
          config,
          label,
        },
      },
    });

  const style = {
    transform: CSS.Transform.toString(transform),
    opacity: isDragging ? 0.8 : undefined,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`p-2 text-primary mb-2 border  rounded cursor-move  bg-secondary transition-colors`}
    >
      <div className="flex items-center gap-2">
        <GripVertical className="w-4 h-4 inline-block" />
        {icon}
        <span className=" text-sm">{label}</span>
      </div>
    </div>
  );
};

export const ComponentLibrary: React.FC<LibraryProps> = () => {
  const [searchTerm, setSearchTerm] = React.useState("");
  const [isMinimized, setIsMinimized] = React.useState(false);
  const defaultGallery = useGalleryStore((state) => state.getDefaultGallery());

  if (!defaultGallery) {
    return null;
  }
  // Map gallery components to sections format
  const sections = React.useMemo(
    () => [
      {
        title: "Agents",
        type: "agent" as ComponentTypes,
        items: defaultGallery.items.components.agents.map((agent) => ({
          label: agent.label,
          config: agent,
        })),
        icon: <Bot className="w-4 h-4" />,
      },
      {
        title: "Models",
        type: "model" as ComponentTypes,
        items: defaultGallery.items.components.models.map((model) => ({
          label: `${model.label || model.config.model}`,
          config: model,
        })),
        icon: <Brain className="w-4 h-4" />,
      },
      {
        title: "Tools",
        type: "tool" as ComponentTypes,
        items: defaultGallery.items.components.tools.map((tool) => ({
          label: tool.config.name,
          config: tool,
        })),
        icon: <Wrench className="w-4 h-4" />,
      },
      {
        title: "Terminations",
        type: "termination" as ComponentTypes,
        items: defaultGallery.items.components.terminations.map(
          (termination) => ({
            label: `${termination.label}`,
            config: termination,
          })
        ),
        icon: <Timer className="w-4 h-4" />,
      },
    ],
    [defaultGallery]
  );

  const items: CollapseProps["items"] = sections.map((section) => {
    const filteredItems = section.items.filter((item) =>
      item.label?.toLowerCase().includes(searchTerm.toLowerCase())
    );

    return {
      key: section.title,
      label: (
        <div className="flex items-center gap-2 font-medium">
          {section.icon}
          <span>{section.title}</span>
          <span className="text-xs text-gray-500">
            ({filteredItems.length})
          </span>
        </div>
      ),
      children: (
        <div className="space-y-2">
          {filteredItems.map((item, itemIndex) => (
            <PresetItem
              key={itemIndex}
              id={`${section.title.toLowerCase()}-${itemIndex}`}
              type={section.type}
              config={item.config}
              label={item.label || ""}
              icon={section.icon}
            />
          ))}
        </div>
      ),
    };
  });

  if (isMinimized) {
    return (
      <div
        onClick={() => setIsMinimized(false)}
        className="absolute group top-4 left-4 bg-primary shadow-md rounded px-4 pr-2 py-2 cursor-pointer transition-all duration-300 z-50 flex items-center gap-2"
      >
        <span>Show Component Library</span>
        <button
          onClick={() => setIsMinimized(false)}
          className="p-1 group-hover:bg-tertiary rounded transition-colors"
          title="Maximize Library"
        >
          <Maximize2 className="w-4 h-4" />
        </button>
      </div>
    );
  }

  return (
    <Sider
      width={300}
      className="bg-primary border z-10 mr-2 border-r border-secondary"
    >
      <div className="rounded p-2 pt-2">
        <div className="flex justify-between items-center mb-2">
          <div className="text-normal">Component Library</div>
          <button
            onClick={() => setIsMinimized(true)}
            className="p-1 hover:bg-tertiary rounded transition-colors"
            title="Minimize Library"
          >
            <Minimize2 className="w-4 h-4" />
          </button>
        </div>

        <div className="mb-4 text-secondary">
          Drag a component to add it to the team
        </div>

        <div className="flex items-center gap-2 mb-4">
          <Input
            placeholder="Search components..."
            onChange={(e) => setSearchTerm(e.target.value)}
            className="flex-1 p-2"
          />
        </div>

        <Collapse
          items={items}
          defaultActiveKey={["Agents"]}
          bordered={false}
          expandIcon={({ isActive }) => (
            <ChevronDown
              strokeWidth={1}
              className={(isActive ? "transform rotate-180" : "") + " w-4 h-4"}
            />
          )}
        />
      </div>
    </Sider>
  );
};

export default ComponentLibrary;
