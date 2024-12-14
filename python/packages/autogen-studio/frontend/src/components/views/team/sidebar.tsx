import React from "react";
import { Button, Tooltip } from "antd";
import {
  Bot,
  Plus,
  Edit,
  Trash2,
  PanelLeftClose,
  PanelLeftOpen,
  Calendar,
  Copy,
  GalleryHorizontalEnd,
  InfoIcon,
  RefreshCcw,
} from "lucide-react";
import type { Team } from "../../types/datamodel";
import { getRelativeTimeString } from "../atoms";
import { defaultTeam } from "./types";
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
  const defaultGallery = useGalleryStore((state) => state.getDefaultGallery());

  const createTeam = () => {
    const newTeam = Object.assign({}, defaultTeam);
    newTeam.config.name = "new_team_" + new Date().getTime();
    onCreateTeam(newTeam);
  };
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
              onClick={createTeam}
              icon={<Plus className="w-4 h-4" />}
            />
          </Tooltip>
        </div>
      </div>
    );
  }

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

      <div className="my-4 flex text-sm  ">
        <div className=" mr-2 w-full">
          <Tooltip title="Create new session">
            <Button
              type="primary"
              className="w-full"
              icon={<Plus className="w-4 h-4" />}
              onClick={createTeam}
            >
              New Team
            </Button>
          </Tooltip>
        </div>
      </div>

      {/* Section Label */}
      <div className="py-2 text-sm text-secondary">
        Recents
        {isLoading && (
          <RefreshCcw className="w-4 h-4 inline-block ml-2 animate-spin" />
        )}
      </div>

      {/* Teams List */}

      {!isLoading && teams.length === 0 && (
        <div className="p-2 mr-2 text-center text-secondary text-sm border border-dashed rounded ">
          <InfoIcon className="w-4 h-4 inline-block mr-1.5 -mt-0.5" />
          No recent teams found
        </div>
      )}

      <div className="scroll overflow-y-auto h-[calc(100%-170px)]">
        <>
          {teams.length > 0 && (
            <div
              key={"teams_title"}
              className={` ${
                isLoading ? "opacity-50 pointer-events-none" : ""
              }`}
            >
              {" "}
              {teams.map((team) => (
                <div key={team.id} className="relative   border-secondary">
                  {
                    <div
                      className={` absolute top-1 left-0.5 z-50 h-[calc(100%-8px)]
               w-1 bg-opacity-80  rounded ${
                 currentTeam?.id === team.id ? "bg-accent" : "bg-tertiary"
               }`}
                    >
                      {" "}
                    </div>
                  }
                  <div
                    className={`group ml-1 flex flex-col p-3 rounded-l cursor-pointer hover:bg-secondary   ${
                      currentTeam?.id === team.id
                        ? "border-accent bg-secondary"
                        : "border-transparent"
                    }`}
                    onClick={() => onSelectTeam(team)}
                  >
                    {/* Team Name and Actions Row */}
                    <div className="flex items-center justify-between">
                      <span className="font-medium truncate">
                        {team.config.name}
                      </span>
                      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        {/* <Tooltip title="Edit team">
                    <Button
                      type="text"
                      size="small"
                      className="p-0 min-w-[24px] h-6"
                      icon={<Edit className="w-4 h-4" />}
                      onClick={(e) => {
                        e.stopPropagation();
                        onEditTeam(team);
                      }}
                    />
                  </Tooltip> */}
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
                      <span className="bg-secondary/20  truncate   rounded">
                        {team.config.team_type}
                      </span>
                      <div className="flex items-center gap-1">
                        <Bot className="w-3 h-3" />
                        <span>
                          {team.config.participants.length}{" "}
                          {team.config.participants.length === 1
                            ? "agent"
                            : "agents"}
                        </span>
                      </div>
                    </div>

                    {/* Updated Timestamp */}
                    {team.updated_at && (
                      <div className="mt-1 flex items-center gap-1 text-xs text-secondary">
                        {/* <Calendar className="w-3 h-3" /> */}
                        <span>{getRelativeTimeString(team.updated_at)}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Gallery Teams Section */}
          <div
            key={"gallery_title"}
            className="py-2 text-sm text-secondary mt-4"
          >
            <GalleryHorizontalEnd className="w-4 h-4 inline-block mr-1.5" />
            From Gallery
          </div>
          <div key={"gallery_content"} className="scroll overflow-y-auto">
            {defaultGallery?.items.teams.map((galleryTeam) => (
              <div
                key={galleryTeam.name + galleryTeam.team_type}
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
                      {galleryTeam.name}
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
                            galleryTeam.name =
                              galleryTeam.name + "_" + new Date().getTime();
                            onCreateTeam({
                              config: galleryTeam,
                            });
                          }}
                        />
                      </Tooltip>
                    </div>
                  </div>

                  {/* Team Metadata Row */}
                  <div className="mt-1 flex items-center gap-2 text-xs text-secondary">
                    <span className="bg-secondary/20 truncate rounded">
                      {galleryTeam.team_type}
                    </span>
                    <div className="flex items-center gap-1">
                      <Bot className="w-3 h-3" />
                      <span>
                        {galleryTeam.participants.length}{" "}
                        {galleryTeam.participants.length === 1
                          ? "agent"
                          : "agents"}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>
      </div>
    </div>
  );
};
