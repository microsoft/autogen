import {
  Component,
  ComponentConfig,
  ComponentTypes,
  TeamConfig,
  AgentConfig,
  ModelConfig,
  ToolConfig,
  WorkbenchConfig,
  TerminationConfig,
  SelectorGroupChatConfig,
  RoundRobinGroupChatConfig,
  AssistantAgentConfig,
  UserProxyAgentConfig,
  MultimodalWebSurferConfig,
  OpenAIClientConfig,
  AzureOpenAIClientConfig,
  AnthropicClientConfig,
  FunctionToolConfig,
  PythonCodeExecutionToolConfig,
  StaticWorkbenchConfig,
  McpWorkbenchConfig,
  StdioServerParams,
  SseServerParams,
  StreamableHttpServerParams,
  MaxMessageTerminationConfig,
  TextMentionTerminationConfig,
  StopMessageTerminationConfig,
  TokenUsageTerminationConfig,
  HandoffTerminationConfig,
  TimeoutTerminationConfig,
  ExternalTerminationConfig,
  SourceMatchTerminationConfig,
  TextMessageTerminationConfig,
  OrTerminationConfig,
  AndTerminationConfig,
} from "./datamodel";
import { PROVIDERS } from "./guards";

// Template interface for component types
export interface ComponentTemplate<T extends ComponentConfig> {
  id: string;
  label: string;
  description: string;
  provider: string;
  component_type: ComponentTypes;
  config: T;
  version?: number;
  component_version?: number;
}

// Team Templates
export const TEAM_TEMPLATES: ComponentTemplate<TeamConfig>[] = [
  {
    id: "round-robin-team",
    label: "Round Robin Team",
    description: "A team where agents take turns in a fixed order",
    provider: PROVIDERS.ROUND_ROBIN_TEAM,
    component_type: "team",
    version: 1,
    component_version: 1,
    config: {
      participants: [],
      termination_condition: {
        provider: PROVIDERS.TEXT_MENTION,
        component_type: "termination",
        config: { text: "TERMINATE" },
      },
      max_turns: 10,
    } as RoundRobinGroupChatConfig,
  },
  {
    id: "selector-team",
    label: "Selector Team",
    description: "A team with a model that selects which agent speaks next",
    provider: PROVIDERS.SELECTOR_TEAM,
    component_type: "team",
    version: 1,
    component_version: 1,
    config: {
      participants: [],
      model_client: {
        provider: PROVIDERS.OPENAI,
        component_type: "model",
        config: { model: "gpt-4o-mini" },
      },
      termination_condition: {
        provider: PROVIDERS.TEXT_MENTION,
        component_type: "termination",
        config: { text: "TERMINATE" },
      },
      max_turns: 10,
      selector_prompt:
        "Select the next speaker based on the conversation context and task requirements.",
      allow_repeated_speaker: true,
    } as SelectorGroupChatConfig,
  },
];

// Agent Templates
export const AGENT_TEMPLATES: ComponentTemplate<AgentConfig>[] = [
  {
    id: "assistant-agent",
    label: "Assistant Agent",
    description: "A helpful AI assistant with tool capabilities",
    provider: PROVIDERS.ASSISTANT_AGENT,
    component_type: "agent",
    version: 2,
    component_version: 2,
    config: {
      name: "assistant_agent",
      description:
        "A helpful AI assistant that can use tools to solve problems",
      system_message:
        "You are a helpful assistant. Solve tasks carefully and methodically. When you have completed the task, say TERMINATE.",
      model_client: {
        provider: PROVIDERS.OPENAI,
        component_type: "model",
        config: { model: "gpt-4o-mini" },
      },
      workbench: [],
      // model_context is optional and complex, omit for now
      reflect_on_tool_use: false,
      tool_call_summary_format: "{result}",
      model_client_stream: false,
    } as AssistantAgentConfig,
  },
  {
    id: "user-proxy-agent",
    label: "User Proxy Agent",
    description: "An agent that represents human input and interaction",
    provider: PROVIDERS.USER_PROXY,
    component_type: "agent",
    version: 1,
    component_version: 1,
    config: {
      name: "user_proxy",
      description: "A human user proxy for providing input and feedback",
    } as UserProxyAgentConfig,
  },
  {
    id: "web-surfer-agent",
    label: "Web Surfer Agent",
    description: "An agent that can browse and interact with web pages",
    provider: PROVIDERS.WEB_SURFER,
    component_type: "agent",
    version: 1,
    component_version: 1,
    config: {
      name: "web_surfer",
      description:
        "An agent that can browse the web and interact with web pages",
      model_client: {
        provider: PROVIDERS.OPENAI,
        component_type: "model",
        config: { model: "gpt-4o" }, // Web surfer needs vision capabilities
      },
      headless: true,
      start_page: "https://www.google.com",
      animate_actions: false,
      to_save_screenshots: false,
      use_ocr: false,
      to_resize_viewport: true,
    } as MultimodalWebSurferConfig,
  },
];

// Model Templates
export const MODEL_TEMPLATES: ComponentTemplate<ModelConfig>[] = [
  {
    id: "openai-gpt-4o-mini",
    label: "OpenAI GPT-4o Mini",
    description: "Fast and cost-effective OpenAI model for most tasks",
    provider: PROVIDERS.OPENAI,
    component_type: "model",
    version: 1,
    component_version: 1,
    config: {
      model: "gpt-4o-mini",
      temperature: 0.7,
      max_tokens: 4096,
    } as OpenAIClientConfig,
  },
  {
    id: "openai-gpt-4o",
    label: "OpenAI GPT-4o",
    description: "Advanced OpenAI model with vision and advanced reasoning",
    provider: PROVIDERS.OPENAI,
    component_type: "model",
    version: 1,
    component_version: 1,
    config: {
      model: "gpt-4o",
      temperature: 0.7,
      max_tokens: 4096,
    } as OpenAIClientConfig,
  },
  {
    id: "azure-openai-gpt-4o-mini",
    label: "Azure OpenAI GPT-4o Mini",
    description: "Azure-hosted OpenAI model for enterprise use",
    provider: PROVIDERS.AZURE_OPENAI,
    component_type: "model",
    version: 1,
    component_version: 1,
    config: {
      model: "gpt-4o-mini",
      azure_endpoint: "https://your-endpoint.openai.azure.com/",
      azure_deployment: "gpt-4o-mini",
      api_version: "2024-06-01",
      temperature: 0.7,
      max_tokens: 4096,
    } as AzureOpenAIClientConfig,
  },
  {
    id: "anthropic-claude-3-sonnet",
    label: "Anthropic Claude-3 Sonnet",
    description: "Anthropic's balanced model for reasoning and creativity",
    provider: PROVIDERS.ANTHROPIC,
    component_type: "model",
    version: 1,
    component_version: 1,
    config: {
      model: "claude-3-5-sonnet-20241022",
      max_tokens: 4096,
      temperature: 0.7,
    } as AnthropicClientConfig,
  },
  {
    id: "external-custom-model",
    label: "External Model",
    description: "Template for a model using an OpenAI-compatible endpoint",
    provider: PROVIDERS.OPENAI,
    component_type: "model",
    version: 1,
    component_version: 1,
    config: {
      model: "your-model-name",
      base_url: "https://example.com/",
      model_info: {
        vision: false,
        function_calling: true,
        json_output: false,
        structured_output: false,
        family: "unknown",
        multiple_system_messages: false,
      },
    } as OpenAIClientConfig,
  },
];

// Tool Templates
export const TOOL_TEMPLATES: ComponentTemplate<ToolConfig>[] = [
  {
    id: "function-tool",
    label: "Function Tool",
    description: "A custom Python function that can be called by agents",
    provider: PROVIDERS.FUNCTION_TOOL,
    component_type: "tool",
    version: 1,
    component_version: 1,
    config: {
      name: "my_function",
      description: "A custom function that performs a specific task",
      source_code: `def my_function(input_text: str) -> str:
    """
    A template function that processes input text.
    
    Args:
        input_text: The text to process
    
    Returns:
        Processed text result
    """
    # Replace this with your custom function logic
    result = f"Processed: {input_text}"
    return result`,
      global_imports: [],
      has_cancellation_support: false,
    } as FunctionToolConfig,
  },
  {
    id: "code-execution-tool",
    label: "Code Execution Tool",
    description: "Execute Python code in a secure environment",
    provider: PROVIDERS.PYTHON_CODE_EXECUTION_TOOL,
    component_type: "tool",
    version: 1,
    component_version: 1,
    config: {
      executor: {
        provider:
          "autogen_ext.code_executors.local.LocalCommandLineCodeExecutor",
        config: {
          timeout: 60,
          work_dir: "./coding",
          functions_module: "functions",
          cleanup_temp_files: true,
        },
      },
      description: "Execute Python code in a secure environment",
      name: "code_execution",
    } as PythonCodeExecutionToolConfig,
  },
];

// Workbench Templates
export const WORKBENCH_TEMPLATES: ComponentTemplate<WorkbenchConfig>[] = [
  {
    id: "static-workbench",
    label: "Static Workbench",
    description: "A workbench with a collection of tools",
    provider: PROVIDERS.STATIC_WORKBENCH,
    component_type: "workbench",
    version: 1,
    component_version: 1,
    config: {
      tools: [],
    } as StaticWorkbenchConfig,
  },
  {
    id: "mcp-stdio-workbench",
    label: "MCP Stdio Server",
    description: "Model Context Protocol server via command line",
    provider: PROVIDERS.MCP_WORKBENCH,
    component_type: "workbench",
    version: 1,
    component_version: 1,
    config: {
      server_params: {
        type: "StdioServerParams",
        command: "npx",
        args: ["@modelcontextprotocol/server-everything"],
        env: {},
        read_timeout_seconds: 30,
      } as StdioServerParams,
    } as McpWorkbenchConfig,
  },
  {
    id: "mcp-sse-workbench",
    label: "MCP SSE Server",
    description: "Model Context Protocol server via server-sent events",
    provider: PROVIDERS.MCP_WORKBENCH,
    component_type: "workbench",
    version: 1,
    component_version: 1,
    config: {
      server_params: {
        type: "SseServerParams",
        url: "http://localhost:3001/sse",
        headers: {
          Authorization: "Bearer your-token-here",
        },
        timeout: 30,
        sse_read_timeout: 30,
      } as SseServerParams,
    } as McpWorkbenchConfig,
  },
  {
    id: "mcp-http-workbench",
    label: "MCP HTTP Server",
    description: "Model Context Protocol server via streamable HTTP",
    provider: PROVIDERS.MCP_WORKBENCH,
    component_type: "workbench",
    version: 1,
    component_version: 1,
    config: {
      server_params: {
        type: "StreamableHttpServerParams",
        url: "http://localhost:3001/mcp",
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer your-token-here",
        },
        timeout: 30,
        sse_read_timeout: 30,
        terminate_on_close: true,
      } as StreamableHttpServerParams,
    } as McpWorkbenchConfig,
  },
];

// Termination Templates
export const TERMINATION_TEMPLATES: ComponentTemplate<TerminationConfig>[] = [
  {
    id: "text-mention-termination",
    label: "Text Mention Termination",
    description: "Terminate when a specific text is mentioned",
    provider: PROVIDERS.TEXT_MENTION,
    component_type: "termination",
    version: 1,
    component_version: 1,
    config: {
      text: "TERMINATE",
    } as TextMentionTerminationConfig,
  },
  {
    id: "max-message-termination",
    label: "Max Message Termination",
    description: "Terminate after a maximum number of messages",
    provider: PROVIDERS.MAX_MESSAGE,
    component_type: "termination",
    version: 1,
    component_version: 1,
    config: {
      max_messages: 10,
      include_agent_event: false,
    } as MaxMessageTerminationConfig,
  },
  {
    id: "stop-message-termination",
    label: "Stop Message Termination",
    description: "Terminate when a StopMessage is received",
    provider: PROVIDERS.STOP_MESSAGE,
    component_type: "termination",
    version: 1,
    component_version: 1,
    config: {} as StopMessageTerminationConfig,
  },
  {
    id: "token-usage-termination",
    label: "Token Usage Termination",
    description: "Terminate when token usage limits are reached",
    provider: PROVIDERS.TOKEN_USAGE,
    component_type: "termination",
    version: 1,
    component_version: 1,
    config: {
      max_total_token: 1000,
    } as TokenUsageTerminationConfig,
  },
  {
    id: "timeout-termination",
    label: "Timeout Termination",
    description: "Terminate after a specified duration",
    provider: PROVIDERS.TIMEOUT,
    component_type: "termination",
    version: 1,
    component_version: 1,
    config: {
      timeout_seconds: 300,
    } as TimeoutTerminationConfig,
  },
  {
    id: "handoff-termination",
    label: "Handoff Termination",
    description: "Terminate when handoff to specific target is detected",
    provider: PROVIDERS.HANDOFF,
    component_type: "termination",
    version: 1,
    component_version: 1,
    config: {
      target: "user",
    } as HandoffTerminationConfig,
  },
  {
    id: "source-match-termination",
    label: "Source Match Termination",
    description: "Terminate when specific sources respond",
    provider: PROVIDERS.SOURCE_MATCH,
    component_type: "termination",
    version: 1,
    component_version: 1,
    config: {
      sources: ["agent1"],
    } as SourceMatchTerminationConfig,
  },
  {
    id: "text-message-termination",
    label: "Text Message Termination",
    description: "Terminate when a TextMessage is received",
    provider: PROVIDERS.TEXT_MESSAGE,
    component_type: "termination",
    version: 1,
    component_version: 1,
    config: {
      source: undefined,
    } as TextMessageTerminationConfig,
  },
  {
    id: "external-termination",
    label: "External Termination",
    description: "Terminate when externally controlled by calling set() method",
    provider: PROVIDERS.EXTERNAL,
    component_type: "termination",
    version: 1,
    component_version: 1,
    config: {} as ExternalTerminationConfig,
  },
  {
    id: "or-termination",
    label: "OR Termination",
    description: "Terminate when any of the conditions are met",
    provider: PROVIDERS.OR_TERMINATION,
    component_type: "termination",
    version: 1,
    component_version: 1,
    config: {
      conditions: [
        {
          provider: PROVIDERS.TEXT_MENTION,
          component_type: "termination",
          config: { text: "TERMINATE" },
        },
        {
          provider: PROVIDERS.MAX_MESSAGE,
          component_type: "termination",
          config: { max_messages: 20 },
        },
      ],
    } as OrTerminationConfig,
  },
  {
    id: "and-termination",
    label: "AND Termination",
    description: "Terminate when all conditions are met",
    provider: PROVIDERS.AND_TERMINATION,
    component_type: "termination",
    version: 1,
    component_version: 1,
    config: {
      conditions: [
        {
          provider: PROVIDERS.TEXT_MENTION,
          component_type: "termination",
          config: { text: "TASK_COMPLETE" },
        },
        {
          provider: PROVIDERS.MAX_MESSAGE,
          component_type: "termination",
          config: { max_messages: 5 },
        },
      ],
    } as AndTerminationConfig,
  },
];

// Main template registry
export const COMPONENT_TEMPLATES = {
  team: TEAM_TEMPLATES,
  agent: AGENT_TEMPLATES,
  model: MODEL_TEMPLATES,
  tool: TOOL_TEMPLATES,
  workbench: WORKBENCH_TEMPLATES,
  termination: TERMINATION_TEMPLATES,
} as const;

// Helper functions
export function getTemplatesForType<T extends ComponentTypes>(
  componentType: T
): ComponentTemplate<ComponentConfig>[] {
  return COMPONENT_TEMPLATES[componentType] || [];
}

export function getTemplateById(
  componentType: ComponentTypes,
  templateId: string
): ComponentTemplate<ComponentConfig> | undefined {
  const templates = COMPONENT_TEMPLATES[componentType];
  return templates.find((template) => template.id === templateId);
}

export function getDefaultTemplate(
  componentType: ComponentTypes
): ComponentTemplate<ComponentConfig> | undefined {
  const templates = COMPONENT_TEMPLATES[componentType];
  return templates[0]; // Return first template as default
}

export function createComponentFromTemplate(
  templateId: string,
  componentType: ComponentTypes,
  overrides?: Partial<Component<ComponentConfig>>
): Component<ComponentConfig> {
  const template = getTemplateById(componentType, templateId);
  if (!template) {
    throw new Error(
      `Template ${templateId} not found for component type ${componentType}`
    );
  }

  return {
    provider: template.provider,
    component_type: template.component_type,
    version: template.version,
    component_version: template.component_version,
    description: template.description,
    config: template.config,
    label: template.label,
    ...overrides,
  };
}

// Workbench-specific helper functions
export interface WorkbenchDropdownOption {
  key: string;
  label: string;
  description: string;
  templateId: string;
}

export function getWorkbenchTemplatesForDropdown(): WorkbenchDropdownOption[] {
  return WORKBENCH_TEMPLATES.map((template) => ({
    key: template.id,
    label: template.label,
    description: template.description,
    templateId: template.id,
  }));
}

export function createWorkbenchFromTemplate(
  templateId: string,
  customLabel?: string
): Component<ComponentConfig> {
  const template = getTemplateById("workbench", templateId);
  if (!template) {
    throw new Error(`Workbench template ${templateId} not found`);
  }

  return createComponentFromTemplate(templateId, "workbench", {
    label: customLabel || `New ${template.label}`,
  });
}

// Generic dropdown option interface
export interface ComponentDropdownOption {
  key: string;
  label: string;
  description: string;
  templateId: string;
}

// Generic helper functions for all component types
export function getTemplatesForDropdown(
  componentType: ComponentTypes
): ComponentDropdownOption[] {
  const templates = getTemplatesForType(componentType);
  return templates.map((template) => ({
    key: template.id,
    label: template.label,
    description: template.description,
    templateId: template.id,
  }));
}

export function createComponentFromTemplateById(
  componentType: ComponentTypes,
  templateId: string,
  customLabel?: string
): Component<ComponentConfig> {
  const template = getTemplateById(componentType, templateId);
  if (!template) {
    throw new Error(`${componentType} template ${templateId} not found`);
  }

  return createComponentFromTemplate(templateId, componentType, {
    label: customLabel || `New ${template.label}`,
  });
}

// Specific helper functions for each component type
export function getTeamTemplatesForDropdown(): ComponentDropdownOption[] {
  return getTemplatesForDropdown("team");
}

export function createTeamFromTemplate(
  templateId: string,
  customLabel?: string
): Component<ComponentConfig> {
  return createComponentFromTemplateById("team", templateId, customLabel);
}

export function getAgentTemplatesForDropdown(): ComponentDropdownOption[] {
  return getTemplatesForDropdown("agent");
}

export function createAgentFromTemplate(
  templateId: string,
  customLabel?: string
): Component<ComponentConfig> {
  return createComponentFromTemplateById("agent", templateId, customLabel);
}

export function getModelTemplatesForDropdown(): ComponentDropdownOption[] {
  return getTemplatesForDropdown("model");
}

export function createModelFromTemplate(
  templateId: string,
  customLabel?: string
): Component<ComponentConfig> {
  return createComponentFromTemplateById("model", templateId, customLabel);
}

export function getToolTemplatesForDropdown(): ComponentDropdownOption[] {
  return getTemplatesForDropdown("tool");
}

export function createToolFromTemplate(
  templateId: string,
  customLabel?: string
): Component<ComponentConfig> {
  return createComponentFromTemplateById("tool", templateId, customLabel);
}

export function getTerminationTemplatesForDropdown(): ComponentDropdownOption[] {
  return getTemplatesForDropdown("termination");
}

export function createTerminationFromTemplate(
  templateId: string,
  customLabel?: string
): Component<ComponentConfig> {
  return createComponentFromTemplateById(
    "termination",
    templateId,
    customLabel
  );
}
