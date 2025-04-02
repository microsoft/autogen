import { config } from "process";
import { Team } from "../../types/datamodel";

export const useTeam = (team: Team) => {
  return {
    id: team.id,
    name: team.config.config.name,
    type: team.config.config.team_type,
    participants: team.config.config.participants,
    updated: team.updated_at,
    config: team.config,

    // Helper methods
    setName: (name: string) => {
      team.config.config.name = name;
    },

    // Computed properties
    agentCount: team.config.config.participants.length,

    // Type guards
    isRoundRobin: () => team.config.config.team_type === "RoundRobinGroupChat",
    isSelector: () => team.config.config.team_type === "SelectorGroupChat",
  };
};

// For creating new teams
export const useTeamCreation = () => {
  const createTeamName = () => `new_team_${new Date().getTime()}`;

  return {
    createTeamName,
    initNewTeam: (baseTeam: Team) => {
      const team = Object.assign({}, baseTeam);
      team.config.config.name = createTeamName();
      return team;
    },
  };
};
