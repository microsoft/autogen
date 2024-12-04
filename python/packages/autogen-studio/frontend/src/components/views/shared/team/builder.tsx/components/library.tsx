import React from "react";
import { Card, Input, Tabs } from "antd";
import { useDraggable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import { Brain, Settings } from "lucide-react";
import { LibraryProps, DragItem } from "../types";
import {
  ComponentTypes,
  ComponentConfigTypes,
  ModelConfig,
  AgentConfig,
  ToolConfig,
  TerminationConfig,
} from "../../../../../types/datamodel";
import { config } from "process";

const { Search } = Input;

interface PresetItemProps {
  id: string;
  type: ComponentTypes;
  config: ComponentConfigTypes;
  label: string;
  icon: React.ReactNode;
}

// Define interfaces for preset items
interface PresetAgent {
  label: string;
  config: AgentConfig;
}

interface PresetModel {
  label: string;
  config: ModelConfig;
}

interface PresetTool {
  label: string;
  config: ToolConfig;
}

interface PresetTermination {
  label: string;
  config: TerminationConfig;
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
          // Add current level
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
      className="p-2   text-primary mb-2 border rounded cursor-move hover:bg-gray-50 transition-colors"
    >
      <div className="flex items-center gap-2">
        {icon}
        <span>{label}</span>
      </div>
    </div>
  );
};

const presetAgents: PresetAgent[] = [
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
];

const presetModels: PresetModel[] = [
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
];

const presetTools = [
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
];

const presetTerminations = [
  {
    label: "Max Message Termination",
    config: {
      termination_type: "MaxMessageTermination",
      max_messages: 10,
    } as TerminationConfig,
  },
];

export const ComponentLibrary: React.FC<LibraryProps> = () => {
  const [searchTerm, setSearchTerm] = React.useState("");

  // Generic filter function that works with both types
  const filterItems = <
    T extends PresetAgent | PresetModel | PresetTermination | PresetTool
  >(
    items: T[]
  ): T[] => {
    if (!searchTerm) return items;
    return items.filter((item) =>
      item.label.toLowerCase().includes(searchTerm.toLowerCase())
    );
  };

  const tabs = [
    {
      key: "agents",
      label: "Agents",
      children: filterItems(presetAgents).map((agent, index) => (
        <PresetItem
          key={index}
          id={`agent-${index}`}
          type="agent"
          config={agent.config}
          label={agent.label}
          icon={<Brain className="w-4 h-4" />}
        />
      )),
    },
    {
      key: "models",
      label: "Models",
      children: filterItems(presetModels).map((model, index) => (
        <PresetItem
          key={index}
          id={`model-${index}`}
          type="model"
          config={model.config}
          label={model.label}
          icon={<Settings className="w-4 h-4" />}
        />
      )),
    },
    {
      key: "tools",
      label: "Tools",
      children: filterItems(presetTools).map((tool, index) => (
        <PresetItem
          key={index}
          id={`tool-${index}`}
          type="tool"
          config={tool.config}
          label={tool.label}
          icon={<Settings className="w-4 h-4" />}
        />
      )),
    },
    {
      key: "terminations",
      label: "Terminations",
      children: filterItems(presetTerminations).map((termination, index) => (
        <PresetItem
          key={index}
          id={`termination-${index}`}
          type="termination"
          config={termination.config}
          label={termination.label}
          icon={<Settings className="w-4 h-4" />}
        />
      )),
    },
  ];

  return (
    <div className="h-full   rounded p-2 pt-2 ">
      <div className="text-normal font-semibold"> Component Library </div>
      <div className="mb-4 text-secondary">
        Drag a component to add it to the team
      </div>
      <div className="mb-4">
        <Search
          placeholder="Search components..."
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>

      <Tabs defaultActiveKey="agents" items={tabs} />
    </div>
  );
};
