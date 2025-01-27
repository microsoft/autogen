import {
  Component,
  RoundRobinGroupChatConfig,
  AssistantAgentConfig,
  UserProxyAgentConfig,
  OpenAIClientConfig,
  FunctionToolConfig,
  MaxMessageTerminationConfig,
  TextMentionTerminationConfig,
  OrTerminationConfig,
} from "../../types/datamodel";
import { Gallery } from "./types";

export const defaultGallery = {
  id: "gallery_default",
  name: "Default Component Gallery",
  metadata: {
    author: "AutoGen Team",
    created_at: "2024-12-12T00:00:00Z",
    updated_at: "2024-12-12T00:00:00Z",
    version: "1.0.0",
    description:
      "A default gallery containing basic components for human-in-loop conversations",
    tags: ["human-in-loop", "assistant"],
    license: "MIT",
    category: "conversation",
  },
  items: {
    teams: [
      {
        provider: "autogen_agentchat.teams.RoundRobinGroupChat",
        component_type: "team",
        version: 1,
        component_version: 1,
        description:
          "A team with an assistant agent and a user agent to enable human-in-loop task completion in a round-robin fashion",
        label: "RoundRobinGroupChat",
        config: {
          participants: [
            {
              provider: "autogen_agentchat.agents.AssistantAgent",
              component_type: "agent",
              version: 1,
              component_version: 1,
              description:
                "An assistant agent that can help users complete tasks",
              label: "AssistantAgent",
              config: {
                name: "assistant_agent",
                model_client: {
                  provider:
                    "autogen_ext.models.openai.OpenAIChatCompletionClient",
                  component_type: "model",
                  version: 1,
                  component_version: 1,
                  description: "A GPT-4o mini model",
                  label: "OpenAIChatCompletionClient",
                  config: {
                    model: "gpt-4o-mini",
                  },
                },
                tools: [
                  {
                    provider: "autogen_core.tools.FunctionTool",
                    component_type: "tool",
                    version: 1,
                    component_version: 1,
                    description:
                      "Create custom tools by wrapping standard Python functions",
                    label: "FunctionTool",
                    config: {
                      name: "calculator",
                      description:
                        "A simple calculator that performs basic arithmetic operations between two numbers",
                      source_code:
                        "def calculator(a: float, b: float, operator: str) -> str:\n    try:\n        if operator == '+':\n            return str(a + b)\n        elif operator == '-':\n            return str(a - b)\n        elif operator == '*':\n            return str(a * b)\n        elif operator == '/':\n            if b == 0:\n                return 'Error: Division by zero'\n            return str(a / b)\n        else:\n            return 'Error: Invalid operator. Please use +, -, *, or /'\n    except Exception as e:\n        return f'Error: {str(e)}'",
                      global_imports: [],
                      has_cancellation_support: false,
                    },
                  },
                ],
                description:
                  "An agent that provides assistance with ability to use tools",
                system_message:
                  "You are a helpful assistant. Solve tasks carefully. You also have a calculator tool which you can use if needed. When the task is done respond with TERMINATE.",
                reflect_on_tool_use: false,
                tool_call_summary_format: "{result}",
              },
            },
            {
              provider: "autogen_agentchat.agents.UserProxyAgent",
              component_type: "agent",
              version: 1,
              component_version: 1,
              description: "A user agent that is driven by a human user",
              label: "UserProxyAgent",
              config: {
                name: "user_agent",
                description: "A user agent that is driven by a human user",
              },
            },
          ],
          termination_condition: {
            provider: "autogen_agentchat.base.OrTerminationCondition",
            component_type: "termination",
            version: 1,
            component_version: 1,
            label: "OrTerminationCondition",
            config: {
              conditions: [
                {
                  provider:
                    "autogen_agentchat.conditions.TextMentionTermination",
                  component_type: "termination",
                  version: 1,
                  component_version: 1,
                  description:
                    "Terminate the conversation when the user mentions 'TERMINATE'",
                  label: "TextMentionTermination",
                  config: {
                    text: "TERMINATE",
                  },
                },
                {
                  provider:
                    "autogen_agentchat.conditions.MaxMessageTermination",
                  component_type: "termination",
                  version: 1,
                  component_version: 1,
                  description: "Terminate the conversation after 10 messages",
                  label: "MaxMessageTermination",
                  config: {
                    max_messages: 10,
                  },
                },
              ],
            },
          },
          max_turns: 1,
        } as RoundRobinGroupChatConfig,
      },
    ],
    components: {
      agents: [
        {
          provider: "autogen_agentchat.agents.AssistantAgent",
          component_type: "agent",
          version: 1,
          component_version: 1,
          description: "An assistant agent that can help users complete tasks",
          label: "AssistantAgent",
          config: {
            name: "assistant_agent",
            model_client: {
              provider: "autogen_ext.models.openai.OpenAIChatCompletionClient",
              component_type: "model",
              version: 1,
              component_version: 1,
              description: "A GPT-4o mini model",
              label: "OpenAIChatCompletionClient",
              config: {
                model: "gpt-4o-mini",
              },
            },
            tools: [
              {
                provider: "autogen_core.tools.FunctionTool",
                component_type: "tool",
                version: 1,
                component_version: 1,
                description:
                  "Create custom tools by wrapping standard Python functions",
                label: "FunctionTool",
                config: {
                  name: "calculator",
                  description:
                    "A simple calculator that performs basic arithmetic operations",
                  source_code:
                    "def calculator(a: float, b: float, operator: str) -> str:\n    try:\n        if operator == '+':\n            return str(a + b)\n        elif operator == '-':\n            return str(a - b)\n        elif operator == '*':\n            return str(a * b)\n        elif operator == '/':\n            if b == 0:\n                return 'Error: Division by zero'\n            return str(a / b)\n        else:\n            return 'Error: Invalid operator. Please use +, -, *, or /'\n    except Exception as e:\n        return f'Error: {str(e)}'",
                  global_imports: [],
                  has_cancellation_support: false,
                },
              },
            ],
            description:
              "An agent that provides assistance with ability to use tools",
            system_message:
              "You are a helpful assistant. Solve tasks carefully. When the task is done respond with TERMINATE.",
            reflect_on_tool_use: false,
            tool_call_summary_format: "{result}",
          } as AssistantAgentConfig,
        },
        {
          provider: "autogen_agentchat.agents.UserProxyAgent",
          component_type: "agent",
          version: 1,
          component_version: 1,
          description: "A user agent that is driven by a human user",
          label: "UserProxyAgent",
          config: {
            name: "user_agent",
            description: "A user agent that is driven by a human user",
          } as UserProxyAgentConfig,
        },
      ],
      models: [
        {
          provider: "autogen_ext.models.openai.OpenAIChatCompletionClient",
          component_type: "model",
          version: 1,
          component_version: 1,
          description: "A GPT-4o mini model",
          label: "OpenAIChatCompletionClient",
          config: {
            model: "gpt-4o-mini",
          } as OpenAIClientConfig,
        },
      ],
      tools: [
        {
          provider: "autogen_core.tools.FunctionTool",
          component_type: "tool",
          version: 1,
          component_version: 1,
          description:
            "Create custom tools by wrapping standard Python functions",
          label: "FunctionTool",
          config: {
            name: "calculator",
            description:
              "A simple calculator that performs basic arithmetic operations",
            source_code:
              "def calculator(a: float, b: float, operator: str) -> str:\n    try:\n        if operator == '+':\n            return str(a + b)\n        elif operator == '-':\n            return str(a - b)\n        elif operator == '*':\n            return str(a * b)\n        elif operator == '/':\n            if b == 0:\n                return 'Error: Division by zero'\n            return str(a / b)\n        else:\n            return 'Error: Invalid operator. Please use +, -, *, or /'\n    except Exception as e:\n        return f'Error: {str(e)}'",
            global_imports: [],
            has_cancellation_support: false,
          } as FunctionToolConfig,
        },
        {
          provider: "autogen_core.tools.FunctionTool",
          component_type: "tool",
          version: 1,
          component_version: 1,
          description:
            "Create custom tools by wrapping standard Python functions",
          label: "FunctionTool",
          config: {
            name: "fetch_website",
            description: "Fetch and return the content of a website URL",
            source_code:
              "async def fetch_website(url: str) -> str:\n    try:\n        import requests\n        from urllib.parse import urlparse\n        \n        # Validate URL format\n        parsed = urlparse(url)\n        if not parsed.scheme or not parsed.netloc:\n            return \"Error: Invalid URL format. Please include http:// or https://\"\n            \n        # Add scheme if not present\n        if not url.startswith(('http://', 'https://')): \n            url = 'https://' + url\n            \n        # Set headers to mimic a browser request\n        headers = {\n            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'\n        }\n        \n        # Make the request with a timeout\n        response = requests.get(url, headers=headers, timeout=10)\n        response.raise_for_status()\n        \n        # Return the text content\n        return response.text\n        \n    except requests.exceptions.Timeout:\n        return \"Error: Request timed out\"\n    except requests.exceptions.ConnectionError:\n        return \"Error: Failed to connect to the website\"\n    except requests.exceptions.HTTPError as e:\n        return f\"Error: HTTP {e.response.status_code} - {e.response.reason}\"\n    except Exception as e:\n        return f\"Error: {str(e)}\"",
            global_imports: [],
            has_cancellation_support: false,
          },
        },
      ],
      terminations: [
        {
          provider: "autogen_agentchat.conditions.TextMentionTermination",
          component_type: "termination",
          version: 1,
          component_version: 1,
          description:
            "Terminate the conversation when the user mentions 'TERMINATE'",
          label: "TextMentionTermination",
          config: {
            text: "TERMINATE",
          } as TextMentionTerminationConfig,
        },
        {
          provider: "autogen_agentchat.conditions.MaxMessageTermination",
          component_type: "termination",
          version: 1,
          component_version: 1,
          description: "Terminate the conversation after 10 messages",
          label: "MaxMessageTermination",
          config: {
            max_messages: 10,
          } as MaxMessageTerminationConfig,
        },
        {
          provider: "autogen_agentchat.base.OrTerminationCondition",
          component_type: "termination",
          version: 1,
          component_version: 1,
          description: "Terminate on either condition",
          label: "OrTerminationCondition",
          config: {
            conditions: [
              {
                provider: "autogen_agentchat.conditions.TextMentionTermination",
                component_type: "termination",
                version: 1,
                component_version: 1,
                description: "Terminate on TERMINATE",
                label: "TextMentionTermination",
                config: {
                  text: "TERMINATE",
                },
              },
              {
                provider: "autogen_agentchat.conditions.MaxMessageTermination",
                component_type: "termination",
                version: 1,
                component_version: 1,
                description: "Terminate after 10 messages",
                label: "MaxMessageTermination",
                config: {
                  max_messages: 10,
                },
              },
            ],
          } as OrTerminationConfig,
        },
      ],
    },
  },
} as Gallery;
