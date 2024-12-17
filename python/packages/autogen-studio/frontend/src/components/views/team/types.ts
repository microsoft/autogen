import type { Team, TeamConfig } from "../../types/datamodel";

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
  name: "default_team",
  participants: [
    {
      component_type: "agent",
      name: "assistant_agent",
      agent_type: "AssistantAgent",
      system_message:
        "You are a helpful assistant. Solve tasks carefully. When done respond with TERMINATE",
      model_client: {
        component_type: "model",
        model: "gpt-4o-2024-08-06",
        model_type: "OpenAIChatCompletionClient",
      },
    },
  ],
  team_type: "RoundRobinGroupChat",
  termination_condition: {
    component_type: "termination",
    termination_type: "MaxMessageTermination",
    max_messages: 3,
  },
};

export const defaultTeam: Team = {
  config: defaultTeamConfig,
};
