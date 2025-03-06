import React, { useState, useEffect } from "react";
import { Button, Dropdown, MenuProps, message, Select, Space } from "antd";
import { Plus, InfoIcon, Bot, TextSearch, ChevronDown } from "lucide-react";
import { Team } from "../../types/datamodel";
import { truncateText } from "../../utils";
import Input from "antd/es/input/Input";

interface NewSessionControlsProps {
  teams: Team[];
  isLoading: boolean;
  onStartSession: (teamId: number, teamName: string) => void;
}

const NewSessionControls = ({
  teams,
  isLoading,
  onStartSession,
}: NewSessionControlsProps) => {
  const [selectedTeamId, setSelectedTeamId] = useState<number | undefined>();
  const [lastUsedTeamId, setLastUsedTeamId] = useState<number | undefined>(
    () => {
      if (typeof window !== "undefined") {
        const stored = localStorage.getItem("lastUsedTeamId");
        return stored ? parseInt(stored) : undefined;
      }
    }
  );
  const [search, setSearch] = useState<string>("");

  console.log(" current teams", teams);
  // Filter teams based on search
  const filteredTeams = teams.filter((team) => {
    return (
      team.component.label?.toLowerCase().includes(search.toLowerCase()) ||
      team.component.description?.toLowerCase().includes(search.toLowerCase())
    );
  });

  // Auto-select last used team on load
  useEffect(() => {
    if (lastUsedTeamId && teams.some((team) => team.id === lastUsedTeamId)) {
      setSelectedTeamId(lastUsedTeamId);
    } else if (teams.length > 0) {
      setSelectedTeamId(teams[0].id);
    }
  }, [teams, lastUsedTeamId]);

  const handleStartSession = async () => {
    if (!selectedTeamId) return;

    if (typeof window !== "undefined") {
      localStorage.setItem("lastUsedTeamId", selectedTeamId.toString());
    }

    const selectedTeam = teams.find((team) => team.id === selectedTeamId);
    if (!selectedTeam) return;

    // Give UI time to update before starting session
    await new Promise((resolve) => setTimeout(resolve, 100));
    onStartSession(selectedTeamId, selectedTeam.component.label || "");
  };

  const handleMenuClick: MenuProps["onClick"] = async (e) => {
    const newTeamId = parseInt(e.key);
    const selectedTeam = teams.find((team) => team.id === newTeamId);

    if (!selectedTeam) {
      console.error("Selected team not found:", newTeamId);
      return;
    }

    // Update state first
    setSelectedTeamId(newTeamId);

    // // Save to localStorage
    // if (typeof window !== "undefined") {
    //   localStorage.setItem("lastUsedTeamId", e.key);
    // }

    // // Delay the session start to allow UI to update
    // await new Promise((resolve) => setTimeout(resolve, 100));
    // onStartSession(newTeamId, selectedTeam.component.label || "");
  };

  const hasNoTeams = !isLoading && teams.length === 0;

  const items: MenuProps["items"] = [
    {
      type: "group",
      label: (
        <div>
          <div className="text-xs text-secondary mb-1">Select a team</div>
          <Input
            prefix={<TextSearch className="w-4 h-4" />}
            placeholder="Search teams"
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      ),
      key: "from-team",
    },
    {
      type: "divider",
    },
    ...filteredTeams.map((team) => ({
      label: (
        <div>
          <div>{truncateText(team.component.label || "", 20)}</div>
          <div className="text-xs text-secondary">
            {team.component.component_type}
          </div>
        </div>
      ),
      key: team?.id?.toString() || "",
      icon: <Bot className="w-4 h-4" />,
    })),
  ];

  const menuProps = {
    items,
    onClick: handleMenuClick,
  };

  const selectedTeam = teams.find((team) => team.id === selectedTeamId);

  return (
    <div className="space-y-2 w-full">
      <Dropdown.Button
        menu={menuProps}
        type="primary"
        className="w-full"
        placement="bottomRight"
        icon={<ChevronDown className="w-4 h-4" />}
        onClick={handleStartSession}
        disabled={!selectedTeamId || isLoading}
      >
        <div className="" style={{ width: "183px" }}>
          <Plus className="w-4 h-4 inline-block -mt-1" /> New Session
        </div>
      </Dropdown.Button>

      <div
        className="text-xs text-secondary"
        title={selectedTeam?.component.label}
      >
        {truncateText(selectedTeam?.component.label || "", 30)}
      </div>

      {hasNoTeams && (
        <div className="flex items-center gap-1.5 text-xs text-yellow-600 mt-1">
          <InfoIcon className="h-3 w-3" />
          <span>Create a team to get started</span>
        </div>
      )}
    </div>
  );
};

export default NewSessionControls;
