import React, { useCallback, useEffect, useState, useContext } from "react";
import { message, Modal } from "antd";
import { ChevronRight } from "lucide-react";
import { appContext } from "../../../hooks/provider";
import { teamAPI } from "./api";
import { useGalleryStore } from "../gallery/store";
import { TeamSidebar } from "./sidebar";
import { Gallery, type Team } from "../../types/datamodel";
import { TeamBuilder } from "./builder/builder";

export const TeamManager: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [teams, setTeams] = useState<Team[]>([]);
  const [currentTeam, setCurrentTeam] = useState<Team | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("teamSidebar");
      return stored !== null ? JSON.parse(stored) : true;
    }
  });

  const [selectedGallery, setSelectedGallery] = useState<Gallery | null>(null);

  const { user } = useContext(appContext);
  const [messageApi, contextHolder] = message.useMessage();
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Persist sidebar state
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("teamSidebar", JSON.stringify(isSidebarOpen));
    }
  }, [isSidebarOpen]);

  const fetchTeams = useCallback(async () => {
    if (!user?.id) return;

    try {
      setIsLoading(true);
      const data = await teamAPI.listTeams(user.id);
      setTeams(data);
      if (!currentTeam && data.length > 0) {
        setCurrentTeam(data[0]);
      }
    } catch (error) {
      console.error("Error fetching teams:", error);
    } finally {
      setIsLoading(false);
    }
  }, [user?.id, currentTeam]);

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

  const handleSelectTeam = async (selectedTeam: Team) => {
    if (!user?.id || !selectedTeam.id) return;

    if (hasUnsavedChanges) {
      Modal.confirm({
        title: "Unsaved Changes",
        content: "You have unsaved changes. Do you want to discard them?",
        okText: "Discard",
        cancelText: "Go Back",
        onOk: () => {
          switchToTeam(selectedTeam.id);
        },
      });
    } else {
      await switchToTeam(selectedTeam.id);
    }
  };

  const switchToTeam = async (teamId: number | undefined) => {
    if (!teamId || !user?.id) return;
    setIsLoading(true);
    try {
      const data = await teamAPI.getTeam(teamId, user.id!);
      setCurrentTeam(data);
      window.history.pushState({}, "", `?teamId=${teamId}`);
    } catch (error) {
      console.error("Error loading team:", error);
      messageApi.error("Failed to load team");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteTeam = async (teamId: number) => {
    if (!user?.id) return;

    try {
      await teamAPI.deleteTeam(teamId, user.id);
      setTeams(teams.filter((t) => t.id !== teamId));
      if (currentTeam?.id === teamId) {
        setCurrentTeam(null);
      }
      messageApi.success("Team deleted");
    } catch (error) {
      console.error("Error deleting team:", error);
      messageApi.error("Error deleting team");
    }
  };

  const handleCreateTeam = (newTeam: Team) => {
    setCurrentTeam(newTeam);
    handleSaveTeam(newTeam);
  };

  const handleSaveTeam = async (teamData: Partial<Team>) => {
    if (!user?.id) return;

    try {
      const sanitizedTeamData = {
        ...teamData,
        created_at: undefined,
        updated_at: undefined,
      };

      const savedTeam = await teamAPI.createTeam(sanitizedTeamData, user.id);
      messageApi.success(
        `Team ${teamData.id ? "updated" : "created"} successfully`
      );

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
      {contextHolder}
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
          setSelectedGallery={setSelectedGallery}
          selectedGallery={selectedGallery}
        />
      </div>

      {/* Main Content */}
      <div
        className={`flex-1 transition-all -mr-6 duration-200 ${
          isSidebarOpen ? "ml-64" : "ml-12"
        }`}
      >
        <div className="p-4 pt-2">
          {/* Breadcrumb */}
          <div className="flex items-center gap-2 mb-4 text-sm">
            <span className="text-primary font-medium">Teams</span>
            {currentTeam && (
              <>
                <ChevronRight className="w-4 h-4 text-secondary" />
                <span className="text-secondary">
                  {currentTeam.component?.label}
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
            <TeamBuilder
              team={currentTeam}
              onChange={handleSaveTeam}
              onDirtyStateChange={setHasUnsavedChanges}
              selectedGallery={selectedGallery}
            />
          ) : (
            <div className="flex items-center justify-center h-[calc(100vh-190px)] text-secondary">
              Select a team from the sidebar or create a new one
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TeamManager;
