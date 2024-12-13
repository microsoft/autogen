import {
  AssistantAgentConfig,
  CombinationTerminationConfig,
  MaxMessageTerminationConfig,
  OpenAIModelConfig,
  PythonFunctionToolConfig,
  RoundRobinGroupChatConfig,
  TextMentionTerminationConfig,
  UserProxyAgentConfig,
} from "../../types/datamodel";

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
        component_type: "team",
        description:
          "A team with an assistant agent and a user agent to enable human-in-loop task completion in a round-robin fashion",
        name: "huma_in_loop_team",
        participants: [
          {
            component_type: "agent",
            description:
              "An assistant agent that can help users complete tasks",
            name: "assistant_agent",
            agent_type: "AssistantAgent",
            system_message:
              "You are a helpful assistant. Solve tasks carefully. You also have a calculator tool which you can use if needed. When the task is done respond with TERMINATE.",
            model_client: {
              component_type: "model",
              description: "A GPT-4o mini model",
              model: "gpt-4o-mini",
              model_type: "OpenAIChatCompletionClient",
            },
            tools: [
              {
                component_type: "tool",
                name: "calculator",
                description:
                  "A simple calculator that performs basic arithmetic operations between two numbers",
                content:
                  "def calculator(a: float, b: float, operator: str) -> str:\n    try:\n        if operator == '+':\n            return str(a + b)\n        elif operator == '-':\n            return str(a - b)\n        elif operator == '*':\n            return str(a * b)\n        elif operator == '/':\n            if b == 0:\n                return 'Error: Division by zero'\n            return str(a / b)\n        else:\n            return 'Error: Invalid operator. Please use +, -, *, or /'\n    except Exception as e:\n        return f'Error: {str(e)}'",
                tool_type: "PythonFunction",
              },
            ],
          },
          {
            component_type: "agent",
            description: "A user agent that is driven by a human user",
            name: "user_agent",
            agent_type: "UserProxyAgent",
            tools: [],
          },
        ],
        team_type: "RoundRobinGroupChat",
        termination_condition: {
          description:
            "Terminate the conversation when the user mentions 'TERMINATE' or after 10 messages",
          component_type: "termination",
          termination_type: "CombinationTermination",
          operator: "or",
          conditions: [
            {
              component_type: "termination",
              description:
                "Terminate the conversation when the user mentions 'TERMINATE'",
              termination_type: "TextMentionTermination",
              text: "TERMINATE",
            },
            {
              component_type: "termination",
              description: "Terminate the conversation after 10 messages",
              termination_type: "MaxMessageTermination",
              max_messages: 10,
            },
          ],
        },
      } as RoundRobinGroupChatConfig,
    ],
    components: {
      agents: [
        {
          component_type: "agent",
          description: "An assistant agent that can help users complete tasks",
          name: "assistant_agent",
          agent_type: "AssistantAgent",
          system_message:
            "You are a helpful assistant. Solve tasks carefully. You also have a calculator tool which you can use if needed. When the task is done respond with TERMINATE.",
          model_client: {
            component_type: "model",
            description: "A GPT-4o mini model",
            model: "gpt-4o-mini",
            model_type: "OpenAIChatCompletionClient",
          },
          tools: [
            {
              component_type: "tool",
              name: "calculator",
              description:
                "A simple calculator that performs basic arithmetic operations between two numbers",
              content:
                "def calculator(a: float, b: float, operator: str) -> str:\n    try:\n        if operator == '+':\n            return str(a + b)\n        elif operator == '-':\n            return str(a - b)\n        elif operator == '*':\n            return str(a * b)\n        elif operator == '/':\n            if b == 0:\n                return 'Error: Division by zero'\n            return str(a / b)\n        else:\n            return 'Error: Invalid operator. Please use +, -, *, or /'\n    except Exception as e:\n        return f'Error: {str(e)}'",
              tool_type: "PythonFunction",
            },
          ],
        } as AssistantAgentConfig,
        {
          component_type: "agent",
          description: "A user agent that is driven by a human user",
          name: "user_agent",
          agent_type: "UserProxyAgent",
          tools: [],
        } as UserProxyAgentConfig,
      ],
      models: [
        {
          component_type: "model",
          description: "A GPT-4o mini model",
          model: "gpt-4o-mini",
          model_type: "OpenAIChatCompletionClient",
        } as OpenAIModelConfig,
      ],
      tools: [
        {
          component_type: "tool",
          name: "calculator",
          description:
            "A simple calculator that performs basic arithmetic operations between two numbers",
          content:
            "def calculator(a: float, b: float, operator: str) -> str:\n    try:\n        if operator == '+':\n            return str(a + b)\n        elif operator == '-':\n            return str(a - b)\n        elif operator == '*':\n            return str(a * b)\n        elif operator == '/':\n            if b == 0:\n                return 'Error: Division by zero'\n            return str(a / b)\n        else:\n            return 'Error: Invalid operator. Please use +, -, *, or /'\n    except Exception as e:\n        return f'Error: {str(e)}'",
          tool_type: "PythonFunction",
        } as PythonFunctionToolConfig,
        {
          component_type: "tool",
          name: "fetch_website",
          description: "Fetch and return the content of a website URL",
          content:
            "async def fetch_website(url: str) -> str:\n    try:\n        import requests\n        from urllib.parse import urlparse\n        \n        # Validate URL format\n        parsed = urlparse(url)\n        if not parsed.scheme or not parsed.netloc:\n            return \"Error: Invalid URL format. Please include http:// or https://\"\n            \n        # Add scheme if not present\n        if not url.startswith(('http://', 'https://')): \n            url = 'https://' + url\n            \n        # Set headers to mimic a browser request\n        headers = {\n            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'\n        }\n        \n        # Make the request with a timeout\n        response = requests.get(url, headers=headers, timeout=10)\n        response.raise_for_status()\n        \n        # Return the text content\n        return response.text\n        \n    except requests.exceptions.Timeout:\n        return \"Error: Request timed out\"\n    except requests.exceptions.ConnectionError:\n        return \"Error: Failed to connect to the website\"\n    except requests.exceptions.HTTPError as e:\n        return f\"Error: HTTP {e.response.status_code} - {e.response.reason}\"\n    except Exception as e:\n        return f\"Error: {str(e)}\"",
          tool_type: "PythonFunction",
        } as PythonFunctionToolConfig,
      ],
      terminations: [
        {
          component_type: "termination",
          description:
            "Terminate the conversation when the user mentions 'TERMINATE'",
          termination_type: "TextMentionTermination",
          text: "TERMINATE",
        } as TextMentionTerminationConfig,
        {
          component_type: "termination",
          description: "Terminate the conversation after 10 messages",
          termination_type: "MaxMessageTermination",
          max_messages: 10,
        } as MaxMessageTerminationConfig,
        {
          component_type: "termination",
          description:
            "Terminate the conversation when the user mentions 'TERMINATE' or after 10 messages",
          termination_type: "CombinationTermination",
          operator: "or",
          conditions: [
            {
              component_type: "termination",
              description:
                "Terminate the conversation when the user mentions 'TERMINATE'",
              termination_type: "TextMentionTermination",
              text: "TERMINATE",
            },
            {
              component_type: "termination",
              description: "Terminate the conversation after 10 messages",
              termination_type: "MaxMessageTermination",
              max_messages: 10,
            },
          ],
        } as CombinationTerminationConfig,
      ],
    },
  },
};
