import type {
  Component,
  ComponentConfig,
  TeamConfig,
  AgentConfig,
  ModelConfig,
  ToolConfig,
  WorkbenchConfig,
  TerminationConfig,
  ChatCompletionContextConfig,
  SelectorGroupChatConfig,
  RoundRobinGroupChatConfig,
  MultimodalWebSurferConfig,
  AssistantAgentConfig,
  UserProxyAgentConfig,
  OpenAIClientConfig,
  AzureOpenAIClientConfig,
  FunctionToolConfig,
  PythonCodeExecutionToolConfig,
  LocalCommandLineCodeExecutorConfig,
  StaticWorkbenchConfig,
  McpWorkbenchConfig,
  OrTerminationConfig,
  MaxMessageTerminationConfig,
  TextMentionTerminationConfig,
  UnboundedChatCompletionContextConfig,
  AnthropicClientConfig,
  AndTerminationConfig,
} from "./datamodel";

// Provider constants
const PROVIDERS = {
  // Teams
  ROUND_ROBIN_TEAM: "autogen_agentchat.teams.RoundRobinGroupChat",
  SELECTOR_TEAM: "autogen_agentchat.teams.SelectorGroupChat",

  // Agents
  ASSISTANT_AGENT: "autogen_agentchat.agents.AssistantAgent",
  USER_PROXY: "autogen_agentchat.agents.UserProxyAgent",
  WEB_SURFER: "autogen_ext.agents.web_surfer.MultimodalWebSurfer",

  // Models
  OPENAI: "autogen_ext.models.openai.OpenAIChatCompletionClient",
  AZURE_OPENAI: "autogen_ext.models.openai.AzureOpenAIChatCompletionClient",
  ANTHROPIC: "autogen_ext.models.anthropic.AnthropicChatCompletionClient",

  // Tools
  FUNCTION_TOOL: "autogen_core.tools.FunctionTool",
  PYTHON_CODE_EXECUTION_TOOL:
    "autogen_ext.tools.code_execution.PythonCodeExecutionTool",

  // Code Executors
  LOCAL_COMMAND_LINE_CODE_EXECUTOR:
    "autogen_ext.code_executors.local.LocalCommandLineCodeExecutor",

  // Workbenches
  STATIC_WORKBENCH: "autogen_core.tools.StaticWorkbench",
  MCP_WORKBENCH: "autogen_ext.tools.mcp.McpWorkbench",

  // Termination
  OR_TERMINATION: "autogen_agentchat.base.OrTerminationCondition",
  AND_TERMINATION: "autogen_agentchat.base.AndTerminationCondition",
  MAX_MESSAGE: "autogen_agentchat.conditions.MaxMessageTermination",
  TEXT_MENTION: "autogen_agentchat.conditions.TextMentionTermination",

  // Contexts
  UNBOUNDED_CONTEXT:
    "autogen_core.model_context.UnboundedChatCompletionContext",
} as const;

// Provider type and mapping
export type Provider = (typeof PROVIDERS)[keyof typeof PROVIDERS];

type ProviderToConfig = {
  // Teams
  [PROVIDERS.SELECTOR_TEAM]: SelectorGroupChatConfig;
  [PROVIDERS.ROUND_ROBIN_TEAM]: RoundRobinGroupChatConfig;
  [PROVIDERS.ANTHROPIC]: AnthropicClientConfig;

  // Agents
  [PROVIDERS.ASSISTANT_AGENT]: AssistantAgentConfig;
  [PROVIDERS.USER_PROXY]: UserProxyAgentConfig;
  [PROVIDERS.WEB_SURFER]: MultimodalWebSurferConfig;

  // Models
  [PROVIDERS.OPENAI]: OpenAIClientConfig;
  [PROVIDERS.AZURE_OPENAI]: AzureOpenAIClientConfig;

  // Tools
  [PROVIDERS.FUNCTION_TOOL]: FunctionToolConfig;
  [PROVIDERS.PYTHON_CODE_EXECUTION_TOOL]: PythonCodeExecutionToolConfig;

  // Code Executors
  [PROVIDERS.LOCAL_COMMAND_LINE_CODE_EXECUTOR]: LocalCommandLineCodeExecutorConfig;

  // Workbenches
  [PROVIDERS.STATIC_WORKBENCH]: StaticWorkbenchConfig;
  [PROVIDERS.MCP_WORKBENCH]: McpWorkbenchConfig;

  // Termination
  [PROVIDERS.OR_TERMINATION]: OrTerminationConfig;
  [PROVIDERS.AND_TERMINATION]: AndTerminationConfig;
  [PROVIDERS.MAX_MESSAGE]: MaxMessageTerminationConfig;
  [PROVIDERS.TEXT_MENTION]: TextMentionTerminationConfig;

  // Contexts
  [PROVIDERS.UNBOUNDED_CONTEXT]: UnboundedChatCompletionContextConfig;
};

// Helper type to get config type from provider
type ConfigForProvider<P extends Provider> = P extends keyof ProviderToConfig
  ? ProviderToConfig[P]
  : never;

export function isComponent(value: any): value is Component<ComponentConfig> {
  return (
    value &&
    typeof value === "object" &&
    "provider" in value &&
    "component_type" in value &&
    "config" in value
  );
}
// Generic component type guard
function isComponentOfType<P extends Provider>(
  component: Component<ComponentConfig>,
  provider: P
): component is Component<ConfigForProvider<P>> {
  return component.provider === provider;
}

// Base component type guards
export function isTeamComponent(
  component: Component<ComponentConfig>
): component is Component<TeamConfig> {
  return component.component_type === "team";
}

export function isAgentComponent(
  component: Component<ComponentConfig>
): component is Component<AgentConfig> {
  return component.component_type === "agent";
}

export function isModelComponent(
  component: Component<ComponentConfig>
): component is Component<ModelConfig> {
  return component.component_type === "model";
}

// NOTE: Tools are now deprecated - use workbenches instead
// This guard is kept for backward compatibility during migration
export function isToolComponent(
  component: Component<ComponentConfig>
): component is Component<ToolConfig> {
  return component.component_type === "tool";
}

export function isTerminationComponent(
  component: Component<ComponentConfig>
): component is Component<TerminationConfig> {
  return component.component_type === "termination";
}

// export function isChatCompletionContextComponent(
//   component: Component<ComponentConfig>
// ): component is Component<ChatCompletionContextConfig> {
//   return component.component_type === "chat_completion_context";
// }

// Team provider guards with proper type narrowing
export function isRoundRobinTeam(
  component: Component<ComponentConfig>
): component is Component<RoundRobinGroupChatConfig> {
  return isComponentOfType(component, PROVIDERS.ROUND_ROBIN_TEAM);
}

export function isSelectorTeam(
  component: Component<ComponentConfig>
): component is Component<SelectorGroupChatConfig> {
  return isComponentOfType(component, PROVIDERS.SELECTOR_TEAM);
}

// Agent provider guards with proper type narrowing
export function isAssistantAgent(
  component: Component<ComponentConfig>
): component is Component<AssistantAgentConfig> {
  return isComponentOfType(component, PROVIDERS.ASSISTANT_AGENT);
}

export function isUserProxyAgent(
  component: Component<ComponentConfig>
): component is Component<UserProxyAgentConfig> {
  return isComponentOfType(component, PROVIDERS.USER_PROXY);
}

export function isWebSurferAgent(
  component: Component<ComponentConfig>
): component is Component<MultimodalWebSurferConfig> {
  return isComponentOfType(component, PROVIDERS.WEB_SURFER);
}

// Model provider guards with proper type narrowing
export function isOpenAIModel(
  component: Component<ComponentConfig>
): component is Component<OpenAIClientConfig> {
  return isComponentOfType(component, PROVIDERS.OPENAI);
}

export function isAzureOpenAIModel(
  component: Component<ComponentConfig>
): component is Component<AzureOpenAIClientConfig> {
  return isComponentOfType(component, PROVIDERS.AZURE_OPENAI);
}
export function isAnthropicModel(
  component: Component<ComponentConfig>
): component is Component<AnthropicClientConfig> {
  return component.provider === PROVIDERS.ANTHROPIC;
}

// Tool provider guards with proper type narrowing
export function isFunctionTool(
  component: Component<ComponentConfig>
): component is Component<FunctionToolConfig> {
  return isComponentOfType(component, PROVIDERS.FUNCTION_TOOL);
}

// Workbench provider guards with proper type narrowing
export function isStaticWorkbench(
  component: Component<ComponentConfig> | null | undefined
): component is Component<StaticWorkbenchConfig> {
  return (
    !!component && isComponentOfType(component, PROVIDERS.STATIC_WORKBENCH)
  );
}

export function isMcpWorkbench(
  component: Component<ComponentConfig> | null | undefined
): component is Component<McpWorkbenchConfig> {
  return !!component && isComponentOfType(component, PROVIDERS.MCP_WORKBENCH);
}

// Termination provider guards with proper type narrowing
export function isOrTermination(
  component: Component<ComponentConfig>
): component is Component<OrTerminationConfig> {
  return isComponentOfType(component, PROVIDERS.OR_TERMINATION);
}

// is Or or And termination
export function isCombinationTermination(
  component: Component<ComponentConfig>
): component is Component<OrTerminationConfig | AndTerminationConfig> {
  return (
    isComponentOfType(component, PROVIDERS.OR_TERMINATION) ||
    isComponentOfType(component, PROVIDERS.AND_TERMINATION)
  );
}

export function isAndTermination(
  component: Component<ComponentConfig>
): component is Component<AndTerminationConfig> {
  return isComponentOfType(component, PROVIDERS.AND_TERMINATION);
}

export function isMaxMessageTermination(
  component: Component<ComponentConfig>
): component is Component<MaxMessageTerminationConfig> {
  return isComponentOfType(component, PROVIDERS.MAX_MESSAGE);
}

export function isTextMentionTermination(
  component: Component<ComponentConfig>
): component is Component<TextMentionTerminationConfig> {
  return isComponentOfType(component, PROVIDERS.TEXT_MENTION);
}

// Context provider guards with proper type narrowing
export function isUnboundedContext(
  component: Component<ComponentConfig>
): component is Component<UnboundedChatCompletionContextConfig> {
  return isComponentOfType(component, PROVIDERS.UNBOUNDED_CONTEXT);
}

// General category type guards
export function isWorkbenchComponent(
  component: Component<ComponentConfig>
): component is Component<WorkbenchConfig> {
  return component.component_type === "workbench";
}

// Runtime assertions
export function assertComponentType<P extends Provider>(
  component: Component<ComponentConfig>,
  provider: P
): asserts component is Component<ConfigForProvider<P>> {
  if (!isComponentOfType(component, provider)) {
    throw new Error(
      `Expected component with provider ${provider}, got ${component.provider}`
    );
  }
}

export { PROVIDERS };
