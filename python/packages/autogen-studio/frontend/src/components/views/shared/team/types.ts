import type { Team, TeamConfig } from "../../../types/datamodel";

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

export const defaultTeamConfig: TeamConfig = {
  version: "1.0.0",
  component_type: "team",
  name: "weather_team",
  participants: [
    {
      component_type: "agent",
      name: "writing_agent",
      agent_type: "AssistantAgent",
      system_message:
        "You are a helpful assistant. Solve tasks carefully. When done respond with TERMINATE",
      model_client: {
        component_type: "model",
        model: "gpt-4o-2024-08-06",
        model_type: "OpenAIChatCompletionClient",
      },
      tools: [
        {
          component_type: "tool",
          name: "get_weather",
          description: "Get the weather for a city",
          content:
            'async def get_weather(city: str) -> str:\n    return f"The weather in {city} is 73 degrees and Sunny."',
          tool_type: "PythonFunction",
        },
      ],
    },
  ],
  team_type: "RoundRobinGroupChat",
  termination_condition: {
    component_type: "termination",
    termination_type: "MaxMessageTermination",
    max_messages: 10,
  },
};
