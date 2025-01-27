import type {
  Component,
  ComponentConfig,
  TeamConfig,
  AgentConfig,
  ModelConfig,
  ToolConfig,
  TerminationConfig,
  ChatCompletionContextConfig,
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
  AZURE_OPENAI:
    "autogen_ext.models.azure_openai.AzureOpenAIChatCompletionClient",

  // Tools
  FUNCTION_TOOL: "autogen_core.tools.FunctionTool",

  // Termination
  OR_TERMINATION: "autogen_agentchat.base.OrTerminationCondition",
  MAX_MESSAGE: "autogen_agentchat.conditions.MaxMessageTermination",
  TEXT_MENTION: "autogen_agentchat.conditions.TextMentionTermination",

  // Contexts
  UNBOUNDED_CONTEXT:
    "autogen_core.model_context.UnboundedChatCompletionContext",
} as const;

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

export function isChatCompletionContextComponent(
  component: Component<ComponentConfig>
): component is Component<ChatCompletionContextConfig> {
  return component.component_type === "chat_completion_context";
}

// Team provider guards
export function isRoundRobinTeam(
  component: Component<ComponentConfig>
): boolean {
  return component.provider === PROVIDERS.ROUND_ROBIN_TEAM;
}

export function isSelectorTeam(component: Component<ComponentConfig>): boolean {
  return component.provider === PROVIDERS.SELECTOR_TEAM;
}

// Agent provider guards
export function isAssistantAgent(
  component: Component<ComponentConfig>
): boolean {
  return component.provider === PROVIDERS.ASSISTANT_AGENT;
}

export function isUserProxyAgent(
  component: Component<ComponentConfig>
): boolean {
  return component.provider === PROVIDERS.USER_PROXY;
}

export function isWebSurferAgent(
  component: Component<ComponentConfig>
): boolean {
  return component.provider === PROVIDERS.WEB_SURFER;
}

// Model provider guards
export function isOpenAIModel(component: Component<ComponentConfig>): boolean {
  return component.provider === PROVIDERS.OPENAI;
}

export function isAzureOpenAIModel(
  component: Component<ComponentConfig>
): boolean {
  return component.provider === PROVIDERS.AZURE_OPENAI;
}

// Tool provider guards
export function isFunctionTool(component: Component<ComponentConfig>): boolean {
  return component.provider === PROVIDERS.FUNCTION_TOOL;
}

// Termination provider guards
export function isOrTermination(
  component: Component<ComponentConfig>
): boolean {
  return component.provider === PROVIDERS.OR_TERMINATION;
}

export function isMaxMessageTermination(
  component: Component<ComponentConfig>
): boolean {
  return component.provider === PROVIDERS.MAX_MESSAGE;
}

export function isTextMentionTermination(
  component: Component<ComponentConfig>
): boolean {
  return component.provider === PROVIDERS.TEXT_MENTION;
}

// Context provider guards
export function isUnboundedContext(
  component: Component<ComponentConfig>
): boolean {
  return component.provider === PROVIDERS.UNBOUNDED_CONTEXT;
}

// Helper function for type narrowing
export function assertComponent<T extends ComponentConfig>(
  component: Component<ComponentConfig>,
  providerCheck: (component: Component<ComponentConfig>) => boolean
): asserts component is Component<T> {
  if (!providerCheck(component)) {
    throw new Error(
      `Component provider ${component.provider} does not match expected type`
    );
  }
}

// Example usage:
// const component: Component<ComponentConfig> = someComponent;
// assertComponent<TeamConfig>(component, isRoundRobinTeam);
// Now TypeScript knows component is Component<TeamConfig>
