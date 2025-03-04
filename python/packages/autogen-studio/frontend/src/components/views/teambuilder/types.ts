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
