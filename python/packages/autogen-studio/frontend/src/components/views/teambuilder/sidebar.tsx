import React, { useState } from "react";
import { Button, Tooltip, Select } from "antd";
import {
  Bot,
  Plus,
  Trash2,
  PanelLeftClose,
  PanelLeftOpen,
  Copy,
  GalleryHorizontalEnd,
  InfoIcon,
  RefreshCcw,
  History,
} from "lucide-react";
import type { Team } from "../../types/datamodel";
import { getRelativeTimeString } from "../atoms";
import { useGalleryStore } from "../gallery/store";

interface TeamSidebarProps {
  isOpen: boolean;
  teams: Team[];
  currentTeam: Team | null;
  onToggle: () => void;
  onSelectTeam: (team: Team) => void;
  onCreateTeam: (team: Team) => void;
  onEditTeam: (team: Team) => void;
  onDeleteTeam: (teamId: number) => void;
  isLoading?: boolean;
}

export const TeamSidebar: React.FC<TeamSidebarProps> = ({
  isOpen,
  teams,
  currentTeam,
  onToggle,
  onSelectTeam,
  onCreateTeam,
  onEditTeam,
  onDeleteTeam,
  isLoading = false,
}) => {
  // Tab state - "recent" or "gallery"
  const [activeTab, setActiveTab] = useState<"recent" | "gallery">("recent");

  // Gallery store
  const {
    galleries,
    selectedGallery,
    selectGallery,
    isLoading: isLoadingGalleries,
  } = useGalleryStore();

  // Render collapsed state
  if (!isOpen) {
    return (
      <div className="h-full border-r border-secondary">
        <div className="p-2 -ml-2">
          <Tooltip title={`Teams (${teams.length})`}>
            <button
              onClick={onToggle}
              className="p-2 rounded-md hover:bg-secondary hover:text-accent text-secondary transition-colors focus:outline-none focus:ring-2 focus:ring-accent focus:ring-opacity-50"
            >
              <PanelLeftOpen strokeWidth={1.5} className="h-6 w-6" />
            </button>
          </Tooltip>
        </div>

        <div className="mt-4 px-2 -ml-1">
          <Tooltip title="Create new team">
            <Button
              type="text"
              className="w-full p-2 flex justify-center"
              onClick={() => createTeam()}
              icon={<Plus className="w-4 h-4" />}
            />
          </Tooltip>
        </div>
      </div>
    );
  }

  const createTeam = () => {
    if (!selectedGallery?.config.components?.teams?.length) {
      return;
    }
    const newTeam = Object.assign(
      {},
      { component: selectedGallery.config.components.teams[0] }
    );
    newTeam.component.label =
      "default_team" + new Date().getTime().toString().slice(0, 2);
    onCreateTeam(newTeam);
  };

  // Render expanded state
  return (
    <div className="h-full border-r border-secondary">
      {/* Header */}
      <div className="flex items-center justify-between pt-0 p-4 pl-2 pr-2 border-b border-secondary">
        <div className="flex items-center gap-2">
          <span className="text-primary font-medium">Teams</span>
          <span className="px-2 py-0.5 text-xs bg-accent/10 text-accent rounded">
            {teams.length}
          </span>
        </div>
        <Tooltip title="Close Sidebar">
          <button
            onClick={onToggle}
            className="p-2 rounded-md hover:bg-secondary hover:text-accent text-secondary transition-colors focus:outline-none focus:ring-2 focus:ring-accent focus:ring-opacity-50"
          >
            <PanelLeftClose strokeWidth={1.5} className="h-6 w-6" />
          </button>
        </Tooltip>
      </div>

      {/* Create Team Button */}
      <div className="my-4 flex text-sm">
        <div className="mr-2 w-full">
          <Tooltip title="Create a new team">
            <Button
              type="primary"
              className="w-full"
              icon={<Plus className="w-4 h-4" />}
              onClick={createTeam}
              disabled={!selectedGallery?.config.components?.teams?.length}
            >
              New Team
            </Button>
          </Tooltip>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex border-b border-secondary">
        <button
          className={`flex items-center px-2 py-1 text-sm font-medium ${
            activeTab === "recent"
              ? "text-accent border-b-2 border-accent"
              : "text-secondary hover:text-primary"
          }`}
          onClick={() => setActiveTab("recent")}
        >
          <History className="w-4 h-4 mr-1.5" />
          Recents
          <span className="ml-1 text-xs">({teams.length})</span>
          {isLoading && activeTab === "recent" && (
            <RefreshCcw className="w-4 h-4 ml-2 animate-spin" />
          )}
        </button>
        <button
          className={`flex items-center px-4 py-2 text-sm font-medium ${
            activeTab === "gallery"
              ? "text-accent border-b-2 border-accent"
              : "text-secondary hover:text-primary"
          }`}
          onClick={() => setActiveTab("gallery")}
        >
          <GalleryHorizontalEnd className="w-4 h-4 mr-1.5" />
          Gallery
          {isLoadingGalleries && activeTab === "gallery" && (
            <RefreshCcw className="w-4 h-4 ml-2 animate-spin" />
          )}
        </button>
      </div>

      <div className="scroll overflow-y-auto h-[calc(100%-200px)]">
        {/* Recents Tab Content */}
        {activeTab === "recent" && (
          <div className="pt-2">
            {!isLoading && teams.length === 0 && (
              <div className="p-2 mr-2 text-center text-secondary text-sm border border-dashed rounded">
                <InfoIcon className="w-4 h-4 inline-block mr-1.5 -mt-0.5" />
                No recent teams found
              </div>
            )}

            {teams.length > 0 && (
              <div className={isLoading ? "pointer-events-none" : ""}>
                {teams.map((team) => (
                  <div key={team.id} className="relative border-secondary">
                    <div
                      className={`absolute top-1 left-0.5 z-50 h-[calc(100%-8px)]
                        w-1 bg-opacity-80 rounded ${
                          currentTeam?.id === team.id
                            ? "bg-accent"
                            : "bg-tertiary"
                        }`}
                    />
                    <div
                      className={`group ml-1 flex flex-col p-3 rounded-l cursor-pointer hover:bg-secondary ${
                        currentTeam?.id === team.id
                          ? "border-accent bg-secondary"
                          : "border-transparent"
                      }`}
                      onClick={() => onSelectTeam(team)}
                    >
                      {/* Team Name and Actions Row */}
                      <div className="flex items-center justify-between">
                        <span className="font-medium truncate">
                          {team.component?.label}
                        </span>
                        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                          <Tooltip title="Delete team">
                            <Button
                              type="text"
                              size="small"
                              className="p-0 min-w-[24px] h-6"
                              danger
                              icon={<Trash2 className="w-4 h-4 text-red-500" />}
                              onClick={(e) => {
                                e.stopPropagation();
                                if (team.id) onDeleteTeam(team.id);
                              }}
                            />
                          </Tooltip>
                        </div>
                      </div>

                      {/* Team Metadata Row */}
                      <div className="mt-1 flex items-center gap-2 text-xs text-secondary">
                        <span className="bg-secondary/20 truncate rounded">
                          {team.component.component_type}
                        </span>
                        <div className="flex items-center gap-1">
                          <Bot className="w-3 h-3" />
                          <span>
                            {team.component.config.participants.length}{" "}
                            {team.component.config.participants.length === 1
                              ? "agent"
                              : "agents"}
                          </span>
                        </div>
                      </div>

                      {/* Updated Timestamp */}
                      {team.updated_at && (
                        <div className="mt-1 flex items-center gap-1 text-xs text-secondary">
                          <span>{getRelativeTimeString(team.updated_at)}</span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Gallery Tab Content */}
        {activeTab === "gallery" && (
          <div className="p-2">
            {/* Gallery Selector */}
            <Select
              className="w-full mb-4"
              placeholder="Select gallery"
              value={selectedGallery?.id}
              onChange={(value) => {
                const gallery = galleries.find((g) => g.id === value);
                if (gallery) selectGallery(gallery);
              }}
              options={galleries.map((gallery) => ({
                value: gallery.id,
                label: gallery.config.name,
              }))}
              loading={isLoadingGalleries}
            />

            {/* Gallery Templates */}
            {selectedGallery?.config.components?.teams.map((galleryTeam) => (
              <div
                key={galleryTeam.label + galleryTeam.component_type}
                className="relative border-secondary"
              >
                <div
                  className={`absolute top-1 left-0.5 z-50 h-[calc(100%-8px)]
                  w-1 bg-opacity-80 rounded bg-tertiary`}
                />
                <div className="group ml-1 flex flex-col p-3 rounded-l cursor-pointer hover:bg-secondary">
                  {/* Team Name and Use Template Action */}
                  <div className="flex items-center justify-between">
                    <span className="font-medium truncate">
                      {galleryTeam.label}
                    </span>
                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <Tooltip title="Use as template">
                        <Button
                          type="text"
                          size="small"
                          className="p-0 min-w-[24px] h-6"
                          icon={<Copy className="w-4 h-4" />}
                          onClick={(e) => {
                            e.stopPropagation();
                            const newTeam = {
                              component: {
                                ...galleryTeam,
                                label: `${galleryTeam.label}_${(
                                  new Date().getTime() + ""
                                ).substring(0, 5)}`,
                              },
                            };
                            onCreateTeam(newTeam);
                          }}
                        />
                      </Tooltip>
                    </div>
                  </div>

                  {/* Team Metadata Row */}
                  <div className="mt-1 flex items-center gap-2 text-xs text-secondary">
                    <span className="bg-secondary/20 truncate rounded">
                      {galleryTeam.component_type}
                    </span>
                    <div className="flex items-center gap-1">
                      <Bot className="w-3 h-3" />
                      <span>
                        {galleryTeam.config.participants.length}{" "}
                        {galleryTeam.config.participants.length === 1
                          ? "agent"
                          : "agents"}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))}

            {!selectedGallery && (
              <div className="p-2 mr-2 text-center text-secondary text-sm border border-dashed rounded">
                <InfoIcon className="w-4 h-4 inline-block mr-1.5 -mt-0.5" />
                Select a gallery to view templates
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

export default TeamSidebar;
