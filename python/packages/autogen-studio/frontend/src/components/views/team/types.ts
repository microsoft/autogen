import type { Component, Team, TeamConfig } from "../../types/datamodel";

export interface TeamEditorProps {
  team?: Team;
  onSave: (team: Partial<Team>) => Promise<void>;
  onCancel: () => void;
  isOpen: boolean;
}

export interface TeamListProps {
  teams: Team[];
  currentTeam?: Team | null;
  onSelect: (team: Team) => void;
  onEdit: (team: Team) => void;
  onDelete: (teamId: number) => void;
  isLoading?: boolean;
}

export const defaultTeamConfig: Component<TeamConfig> = {
  provider: "autogen_agentchat.teams.RoundRobinGroupChat",
  component_type: "team",
  version: 1,
  component_version: 1,
  description:
    "A team of agents that chat with users in a round-robin fashion.",
  label: "General Team",
  config: {
    participants: [
      {
        provider: "autogen_agentchat.agents.AssistantAgent",
        component_type: "agent",
        version: 1,
        component_version: 1,
        config: {
          name: "weather_agent",
          model_client: {
            provider: "autogen_ext.models.openai.OpenAIChatCompletionClient",
            component_type: "model",
            version: 1,
            component_version: 1,
            config: { model: "gpt-4o-mini" },
          },
          tools: [
            {
              provider: "autogen_core.tools.FunctionTool",
              component_type: "tool",
              version: 1,
              component_version: 1,
              config: {
                source_code:
                  'async def get_weather(city: str) -> str:\n    return f"The weather in {city} is 73 degrees and Sunny."\n',
                name: "get_weather",
                description: "",
                global_imports: [],
                has_cancellation_support: false,
              },
            },
          ],
          handoffs: [],
          description:
            "An agent that provides assistance with ability to use tools.",
          system_message:
            "You are a helpful AI assistant. Solve tasks using your tools. Reply with TERMINATE when the task has been completed.",
          reflect_on_tool_use: false,
          tool_call_summary_format: "{result}",
        },
      },
    ],
    termination_condition: {
      provider: "autogen_agentchat.base.OrTerminationCondition",
      component_type: "termination",
      version: 1,
      component_version: 1,
      config: {
        conditions: [
          {
            provider: "autogen_agentchat.conditions.MaxMessageTermination",
            component_type: "termination",
            version: 1,
            component_version: 1,
            config: { max_messages: 10 },
          },
          {
            provider: "autogen_agentchat.conditions.TextMentionTermination",
            component_type: "termination",
            version: 1,
            component_version: 1,
            config: { text: "TERMINATE" },
          },
        ],
      },
    },
    max_turns: 1,
  },
};

export const defaultTeam: Team = {
  component: defaultTeamConfig,
};
