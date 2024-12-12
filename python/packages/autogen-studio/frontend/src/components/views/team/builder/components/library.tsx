import React from "react";
import { Input, Collapse, type CollapseProps } from "antd";
import { useDraggable } from "@dnd-kit/core";
import { CSS } from "@dnd-kit/utilities";
import {
  Brain,
  Settings,
  FoldVertical,
  ChevronDown,
  Bot,
  Wrench,
  Timer,
  Maximize2,
  MinimizeIcon,
  Minimize2,
} from "lucide-react";
import {
  AgentConfig,
  ModelConfig,
  TerminationConfig,
  ToolConfig,
} from "../../../../types/datamodel";
import Sider from "antd/es/layout/Sider";

// Types
interface ComponentConfigTypes {
  [key: string]: any;
}

type ComponentTypes = "agent" | "model" | "tool" | "termination";

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
      className="p-2 text-primary mb-2 border border-secondary rounded cursor-move hover:bg-secondary transition-colors"
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
  const [isMinimized, setIsMinimized] = React.useState(false);

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
            name: "assistant_agent",
            agent_type: "AssistantAgent",
            system_message:
              "You are a helpful assistant. Solve tasks carefully.",
            model_client: {
              component_type: "model",
              model: "gpt-4o-mini",
              model_type: "OpenAIChatCompletionClient",
            },
          } as AgentConfig,
        },
        {
          label: "User Proxy Agent",
          config: {
            name: "user_agent",
            agent_type: "UserProxyAgent",
          } as AgentConfig,
        },
      ],
      icon: <Bot className="w-4 h-4" />,
    },
    {
      title: "Models",
      type: "model",
      items: [
        {
          label: "OpenAI GPT4o-mini",
          config: {
            model: "gpt-4o-mini",
            model_type: "OpenAIChatCompletionClient",
          } as ModelConfig,
        },
        {
          label: "OpenAI GPT4o",
          config: {
            model: "gpt-4o",
            model_type: "OpenAIChatCompletionClient",
          } as ModelConfig,
        },
      ],
      icon: <Brain className="w-4 h-4" />,
    },
    {
      title: "Tools",
      type: "tool",
      items: [
        {
          label: "Calculator Tool",
          config: {
            component_type: "tool",
            name: "calculator",
            description:
              "Perform basic arithmetic operations (+, -, *, /) between two numbers",
            content:
              "async def calculator(num1: float, num2: float, operation: str) -> str:\n    operations = {\n        '+': lambda x, y: x + y,\n        '-': lambda x, y: x - y,\n        '*': lambda x, y: x * y,\n        '/': lambda x, y: x / y if y != 0 else 'Error: Division by zero'\n    }\n    \n    if operation not in operations:\n        return f\"Error: Invalid operation. Please use one of: {', '.join(operations.keys())}\"\n    \n    try:\n        result = operations[operation](num1, num2)\n        return f\"{num1} {operation} {num2} = {result}\"\n    except Exception as e:\n        return f\"Error: {str(e)}\"",
            tool_type: "PythonFunction",
          } as ToolConfig,
        },
        {
          label: "Fetch Website",
          config: {
            component_type: "tool",
            name: "fetch_website",
            description: "Fetch and return the content of a website URL",
            content:
              "async def fetch_website(url: str) -> str:\n    try:\n        import requests\n        from urllib.parse import urlparse\n        \n        # Validate URL format\n        parsed = urlparse(url)\n        if not parsed.scheme or not parsed.netloc:\n            return \"Error: Invalid URL format. Please include http:// or https://\"\n            \n        # Add scheme if not present\n        if not url.startswith(('http://', 'https://')): \n            url = 'https://' + url\n            \n        # Set headers to mimic a browser request\n        headers = {\n            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'\n        }\n        \n        # Make the request with a timeout\n        response = requests.get(url, headers=headers, timeout=10)\n        response.raise_for_status()\n        \n        # Return the text content\n        return response.text\n        \n    except requests.exceptions.Timeout:\n        return \"Error: Request timed out\"\n    except requests.exceptions.ConnectionError:\n        return \"Error: Failed to connect to the website\"\n    except requests.exceptions.HTTPError as e:\n        return f\"Error: HTTP {e.response.status_code} - {e.response.reason}\"\n    except Exception as e:\n        return f\"Error: {str(e)}\"",
            tool_type: "PythonFunction",
          } as ToolConfig,
        },
      ],
      icon: <Wrench className="w-4 h-4" />,
    },
    {
      title: "Terminations",
      type: "termination",
      items: [
        {
          label: "10 Max Message Termination",
          config: {
            termination_type: "MaxMessageTermination",
            max_messages: 10,
          } as TerminationConfig,
        },
        {
          label: "Text Message Termination",
          config: {
            termination_type: "TextMentionTermination",
            text: "TERMINATE",
          } as TerminationConfig,
        },
        {
          label: "Max or Text Termination",
          config: {
            component_type: "termination",
            termination_type: "CombinationTermination",
            operator: "or",
            conditions: [
              {
                component_type: "termination",
                termination_type: "TextMentionTermination",
                text: "TERMINATE",
              },
              {
                component_type: "termination",
                termination_type: "MaxMessageTermination",
                max_messages: 10,
              },
            ],
          } as TerminationConfig,
        },
      ],
      icon: <Timer className="w-4 h-4" />,
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

  if (isMinimized) {
    return (
      <div
        onClick={() => setIsMinimized(false)}
        className="absolute group top-4 left-4 bg-primary shadow-md rounded px-4 pr-2 py-2 cursor-pointer   transition-all duration-300 z-50 flex items-center gap-2"
      >
        <span>Show Component Library</span>

        <button
          onClick={() => setIsMinimized(false)}
          className="p-1 group-hover:bg-tertiary rounded transition-colors "
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
      className="bg-primary z-10 mr-2 border-r border-secondary"
    >
      <div className="rounded p-2 pt-2">
        <div className="flex justify-between items-center mb-2">
          <div className="text-normal  ">Component Library</div>
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
