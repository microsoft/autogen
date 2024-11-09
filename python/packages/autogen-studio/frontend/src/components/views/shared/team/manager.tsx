import React, { useCallback, useEffect, useState, useContext } from "react";
import { Button, message, Badge } from "antd";
import { Plus } from "lucide-react";
import { appContext } from "../../../../hooks/provider";
import { teamAPI } from "./api";
import { TeamList } from "./list";
import { TeamEditor } from "./editor";
import type { Team } from "../../../types/datamodel";

export const TeamManager: React.FC = () => {
  // UI State
  const [isLoading, setIsLoading] = useState(false);
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [editingTeam, setEditingTeam] = useState<Team | undefined>();
  const [teams, setTeams] = useState<Team[]>([]);
  const [currentTeam, setCurrentTeam] = useState<Team | null>(null);

  // Global context
  const { user } = useContext(appContext);

  // Fetch all teams
  const fetchTeams = useCallback(async () => {
    if (!user?.email) return;

    try {
      setIsLoading(true);
      const data = await teamAPI.listTeams(user.email);
      setTeams(data);
      if (!currentTeam && data.length > 0) {
        setCurrentTeam(data[0]);
      }
    } catch (error) {
      console.error("Error fetching teams:", error);
      message.error("Error loading teams");
    } finally {
      setIsLoading(false);
    }
  }, [user?.email, currentTeam]);

  // Handle team operations
  const handleSaveTeam = async (teamData: Partial<Team>) => {
    if (!user?.email) return;

    try {
      console.log("teamData", teamData);
      const savedTeam = await teamAPI.createTeam(teamData, user.email);

      // Update teams list
      if (teamData.id) {
        setTeams(teams.map((t) => (t.id === savedTeam.id ? savedTeam : t)));
        if (currentTeam?.id === savedTeam.id) {
          setCurrentTeam(savedTeam);
        }
      } else {
        setTeams([...teams, savedTeam]);
      }

      setIsEditorOpen(false);
      setEditingTeam(undefined);
    } catch (error) {
      throw error;
    }
  };

  const handleDeleteTeam = async (teamId: number) => {
    if (!user?.email) return;

    try {
      await teamAPI.deleteTeam(teamId, user.email);
      setTeams(teams.filter((t) => t.id !== teamId));
      if (currentTeam?.id === teamId) {
        setCurrentTeam(null);
      }
      message.success("Team deleted");
    } catch (error) {
      console.error("Error deleting team:", error);
      message.error("Error deleting team");
    }
  };

  const handleSelectTeam = async (selectedTeam: Team) => {
    if (!user?.email || !selectedTeam.id) return;

    try {
      setIsLoading(true);
      const data = await teamAPI.getTeam(selectedTeam.id, user.email);
      setCurrentTeam(data);
    } catch (error) {
      console.error("Error loading team:", error);
      message.error("Error loading team");
    } finally {
      setIsLoading(false);
    }
  };

  // Load teams on mount
  useEffect(() => {
    fetchTeams();
  }, [fetchTeams]);

  // Content component
  const TeamContent = () => (
    <div className="flex gap-2 items-center">
      {teams && teams.length > 0 && (
        <div className="flex items-center gap-3">
          <TeamList
            teams={teams}
            currentTeam={currentTeam}
            onSelect={handleSelectTeam}
            onEdit={(team) => {
              setEditingTeam(team);
              setIsEditorOpen(true);
            }}
            onDelete={handleDeleteTeam}
            isLoading={isLoading}
          />
        </div>
      )}
      <Button
        type="primary"
        onClick={() => {
          setEditingTeam(undefined);
          setIsEditorOpen(true);
        }}
        icon={<Plus className="w-4 h-4" />}
      >
        New Team
      </Button>
    </div>
  );

  return (
    <>
      <div className="bg-secondary rounded p-2">
        <div className="text-xs pb-2">
          Teams <span className="px-1 text-accent">{teams.length} </span>
        </div>
        <TeamContent />
      </div>
      <TeamEditor
        team={editingTeam}
        isOpen={isEditorOpen}
        onSave={handleSaveTeam}
        onCancel={() => {
          setIsEditorOpen(false);
          setEditingTeam(undefined);
        }}
      />
    </>
  );
};

export default TeamManager;
