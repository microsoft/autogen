import React, { useCallback, useEffect, useState, useContext } from "react";
import { Button, message } from "antd";
import { ChevronRight } from "lucide-react";
import { appContext } from "../../../../hooks/provider";
import { teamAPI } from "./api";
import { TeamSidebar } from "./sidebar";
import type { Team } from "../../../types/datamodel";
import { defaultTeam } from "./types";
import { TeamBuilder } from "./builder/builder";

export const TeamManager: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [teams, setTeams] = useState<Team[]>([]);
  const [currentTeam, setCurrentTeam] = useState<Team | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => {
    const stored = localStorage.getItem("teamSidebar");
    return stored !== null ? JSON.parse(stored) : true;
  });

  const { user } = useContext(appContext);

  // Persist sidebar state
  useEffect(() => {
    localStorage.setItem("teamSidebar", JSON.stringify(isSidebarOpen));
  }, [isSidebarOpen]);

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
    } finally {
      setIsLoading(false);
    }
  }, [user?.email]);

  useEffect(() => {
    fetchTeams();
  }, [fetchTeams]);

  // Handle URL params
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const teamId = params.get("teamId");

    if (teamId && !currentTeam) {
      handleSelectTeam({ id: parseInt(teamId) } as Team);
    }
  }, []);

  useEffect(() => {
    const handleLocationChange = () => {
      const params = new URLSearchParams(window.location.search);
      const teamId = params.get("teamId");

      if (!teamId && currentTeam) {
        setCurrentTeam(null);
      }
    };

    window.addEventListener("popstate", handleLocationChange);
    return () => window.removeEventListener("popstate", handleLocationChange);
  }, [currentTeam]);

  const handleSelectTeam = async (selectedTeam: Team) => {
    if (!user?.email || !selectedTeam.id) return;

    try {
      setIsLoading(true);
      const data = await teamAPI.getTeam(selectedTeam.id, user.email);
      setCurrentTeam(data);
      window.history.pushState({}, "", `?teamId=${selectedTeam.id}`);
    } catch (error) {
      console.error("Error loading team:", error);
    } finally {
      setIsLoading(false);
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

  const handleCreateTeam = () => {
    const newTeam = Object.assign({}, defaultTeam);
    newTeam.config.name = "new_team_" + new Date().getTime();
    setCurrentTeam(newTeam);
  };

  // const handleSaveTeam = async (teamData: Partial<Team>) => {
  //   if (!user?.email) return;

  //   try {
  //     const savedTeam = await teamAPI.createTeam(teamData, user.email);

  //     if (teamData.id) {
  //       setTeams(teams.map((t) => (t.id === savedTeam.id ? savedTeam : t)));
  //       if (currentTeam?.id === savedTeam.id) {
  //         setCurrentTeam(savedTeam);
  //       }
  //     } else {
  //       setTeams([savedTeam, ...teams]);
  //       setCurrentTeam(savedTeam);
  //       window.history.pushState({}, "", `?teamId=${savedTeam.id}`);
  //     }
  //   } catch (error) {
  //     throw error;
  //   }
  // };
  const handleSaveTeam = async (teamData: Partial<Team>) => {
    if (!user?.email) return;

    try {
      console.log("teamData", teamData);
      const savedTeam = await teamAPI.createTeam(teamData, user.email);

      message.success(
        `Team ${teamData.id ? "updated" : "created"} successfully`
      );

      // Update teams list
      if (teamData.id) {
        setTeams(teams.map((t) => (t.id === savedTeam.id ? savedTeam : t)));
        if (currentTeam?.id === savedTeam.id) {
          setCurrentTeam(savedTeam);
        }
      } else {
        setTeams([savedTeam, ...teams]);
        setCurrentTeam(savedTeam);
      }
    } catch (error) {
      throw error;
    }
  };

  return (
    <div className="relative flex h-full w-full">
      {/* Sidebar */}
      <div
        className={`absolute left-0 top-0 h-full transition-all duration-200 ease-in-out ${
          isSidebarOpen ? "w-64" : "w-12"
        }`}
      >
        <TeamSidebar
          isOpen={isSidebarOpen}
          teams={teams}
          currentTeam={currentTeam}
          onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
          onSelectTeam={handleSelectTeam}
          onCreateTeam={handleCreateTeam}
          onEditTeam={setCurrentTeam}
          onDeleteTeam={handleDeleteTeam}
          isLoading={isLoading}
        />
      </div>

      {/* Main Content */}
      <div
        className={`flex-1 transition-all duration-200 ${
          isSidebarOpen ? "ml-64" : "ml-12"
        }`}
      >
        <div className="p-4 pt-2">
          {/* Breadcrumb */}
          <div className="flex items-center gap-2 mb-4 text-sm">
            <span className="text-primary font-medium"> Teams</span>
            {currentTeam && (
              <>
                <ChevronRight className="w-4 h-4 text-secondary" />
                <span className="text-secondary">
                  {currentTeam.config.name}
                  {currentTeam.id ? (
                    ""
                  ) : (
                    <span className="text-xs text-orange-500"> (New)</span>
                  )}
                </span>
              </>
            )}
          </div>

          {/* Content Area */}
          {currentTeam ? (
            <TeamBuilder team={currentTeam} onChange={handleSaveTeam} />
          ) : (
            <div className="flex items-center justify-center h-[calc(100vh-120px)] text-secondary">
              Select a team from the sidebar or create a new one
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TeamManager;
