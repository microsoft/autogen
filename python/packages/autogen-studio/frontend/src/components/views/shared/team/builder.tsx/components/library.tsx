import React from "react";
import { Input, Collapse, type CollapseProps } from "antd";
import { useDraggable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import { Brain, Settings, FoldVertical, ChevronDown } from "lucide-react";

// Types
interface ComponentConfigTypes {
  [key: string]: any;
}

type ComponentTypes = "agent" | "model" | "tool" | "termination";

interface AgentConfig {
  name: string;
  agent_type: string;
  system_message: string;
}

interface ModelConfig {
  model: string;
  model_type: string;
}

interface ToolConfig {
  name: string;
  description: string;
  tool_type: string;
}

interface TerminationConfig {
  termination_type: string;
  max_messages: number;
}

interface LibraryProps {}

interface PresetItemProps {
  id: string;
  type: ComponentTypes;
  config: ComponentConfigTypes;
  label: string;
  icon: React.ReactNode;
}

interface SectionItem {
  label: string;
  config: ComponentConfigTypes;
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
    opacity: isDragging ? 0.5 : undefined,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className="p-2 text-primary mb-2 border rounded cursor-move hover:bg-secondary transition-colors"
    >
      <div className="flex items-center gap-2">
        {icon}
        <span>{label}</span>
      </div>
    </div>
  );
};

export const ComponentLibrary: React.FC<LibraryProps> = () => {
  const [searchTerm, setSearchTerm] = React.useState("");

  const sections: Array<{
    title: string;
    items: SectionItem[];
    icon: React.ReactNode;
    type: ComponentTypes;
  }> = [
    {
      title: "Agents",
      type: "agent",
      items: [
        {
          label: "Assistant Agent",
          config: {
            name: "Assistant",
            agent_type: "AssistantAgent",
            system_message: "You are a helpful assistant.",
          } as AgentConfig,
        },
        {
          label: "User Proxy Agent",
          config: {
            name: "User Proxy",
            agent_type: "UserProxyAgent",
            system_message: "Human user proxy",
          } as AgentConfig,
        },
      ],
      icon: <Brain className="w-4 h-4" />,
    },
    {
      title: "Models",
      type: "model",
      items: [
        {
          label: "OpenAI GPT-4",
          config: {
            model: "gpt-4",
            model_type: "OpenAIChatCompletionClient",
          } as ModelConfig,
        },
        {
          label: "OpenAI GPT-3.5",
          config: {
            model: "gpt-3.5-turbo",
            model_type: "OpenAIChatCompletionClient",
          } as ModelConfig,
        },
      ],
      icon: <Settings className="w-4 h-4" />,
    },
    {
      title: "Tools",
      type: "tool",
      items: [
        {
          label: "Weather Tool",
          config: {
            name: "Weather Tool",
            description: "Tool 1 description",
            tool_type: "PythonFunction",
          } as ToolConfig,
        },
        {
          label: "News Tool",
          config: {
            name: "News Tool",
            description: "Tool 2 description",
            tool_type: "PythonFunction",
          } as ToolConfig,
        },
      ],
      icon: <Settings className="w-4 h-4" />,
    },
    {
      title: "Terminations",
      type: "termination",
      items: [
        {
          label: "Max Message Termination",
          config: {
            termination_type: "MaxMessageTermination",
            max_messages: 10,
          } as TerminationConfig,
        },
        {
          label: "Max Message Termination",
          config: {
            termination_type: "MaxMessageTermination",
            max_messages: 10,
          } as TerminationConfig,
        },
      ],
      icon: <Settings className="w-4 h-4" />,
    },
  ];

  const items: CollapseProps["items"] = sections.map((section, index) => {
    const filteredItems = section.items.filter((item) =>
      item.label.toLowerCase().includes(searchTerm.toLowerCase())
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
              label={item.label}
              icon={section.icon}
            />
          ))}
        </div>
      ),
    };
  });

  return (
    <div className="rounded p-2 pt-2">
      <div className="text-normal font-semibold">Component Library</div>
      <div className="mb-4 text-secondary">
        Drag a component to add it to the team
      </div>

      <div className="flex items-center gap-2 mb-4 ">
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
            className={isActive ? "transform rotate-180" : ""}
          />
        )}
        // className="bg-tertiary rounded"
      />
    </div>
  );
};

export default ComponentLibrary;
