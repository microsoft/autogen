import React from "react";
import { Button, Tooltip } from "antd";
import {
  Plus,
  Edit,
  Trash2,
  PanelLeftClose,
  PanelLeftOpen,
  InfoIcon,
  RefreshCcw,
} from "lucide-react";
import type { Session, Team } from "../../types/datamodel";
import { getRelativeTimeString } from "../atoms";
import NewSessionControls from "./newsession";

interface SidebarProps {
  isOpen: boolean;
  sessions: Session[];
  currentSession: Session | null;
  onToggle: () => void;
  onSelectSession: (session: Session) => void;
  onEditSession: (session?: Session) => void;
  onDeleteSession: (sessionId: number) => void;
  isLoading?: boolean;
  onStartSession: (teamId: number, teamName: string) => void;
  teams: Team[];
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  sessions,
  currentSession,
  onToggle,
  onSelectSession,
  onEditSession,
  onDeleteSession,
  isLoading = false,
  onStartSession,
  teams,
}) => {
  if (!isOpen) {
    return (
      <div className="h-full  border-r border-secondary">
        <div className="p-2 -ml-2 ">
          <Tooltip
            title=<span>
              Sessions{" "}
              <span className="text-accent mx-1"> {sessions.length} </span>{" "}
            </span>
          >
            <button
              onClick={onToggle}
              className="p-2 rounded-md hover:bg-secondary hover:text-accent text-secondary transition-colors focus:outline-none focus:ring-2 focus:ring-accent focus:ring-opacity-50"
            >
              <PanelLeftOpen strokeWidth={1.5} className="h-6 w-6" />
            </button>
          </Tooltip>
        </div>
        <div className="mt-4 px-2 -ml-1">
          <Tooltip title="Create new session">
            <Button
              type="text"
              className="w-full p-2 flex justify-center"
              onClick={() => onEditSession()}
              icon={<Plus className="w-4 h-4" />}
            />
          </Tooltip>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full border-r border-secondary ">
      <div className="flex items-center justify-between pt-0 p-4 pl-2 pr-2 border-b border-secondary">
        <div className="flex items-center gap-2">
          <span className="text-primary font-medium">Sessions</span>
          <span className="px-2 py-0.5 text-xs bg-accent/10 text-accent rounded">
            {sessions.length}
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

      <div className="my-4 flex text-sm  ">
        <div className=" mr-2 w-full pr-2">
          {isOpen && (
            <NewSessionControls
              teams={teams}
              isLoading={isLoading}
              onStartSession={onStartSession}
            />
          )}
        </div>
      </div>

      <div className="py-2 flex text-sm text-secondary">
        Recents{" "}
        {isLoading && (
          <RefreshCcw className="w-4 h-4 inline-block ml-2 animate-spin" />
        )}
      </div>

      {/* no sessions found */}

      {!isLoading && sessions.length === 0 && (
        <div className="p-2 mr-2 text-center text-secondary text-sm border border-dashed rounded ">
          <InfoIcon className="w-4 h-4 inline-block mr-1.5 -mt-0.5" />
          No recent sessions found
        </div>
      )}

      <div className="overflow-y-auto   h-[calc(100%-150px)]">
        {sessions.map((s) => (
          <div key={s.id} className="relative">
            <div
              className={`bg-accent absolute top-1 left-0.5 z-50 h-[calc(100%-8px)]
               w-1 bg-opacity-80  rounded ${
                 currentSession?.id === s.id ? "bg-accent" : "bg-tertiary"
               }`}
            >
              {" "}
            </div>
            <div
              className={`group ml-1 flex items-center justify-between rounded-l p-2 py-1 text-sm cursor-pointer hover:bg-tertiary ${
                currentSession?.id === s.id ? "border-accent bg-secondary" : ""
              }`}
              onClick={() => onSelectSession(s)}
            >
              <div className="flex flex-col min-w-0 flex-1 mr-2">
                <div className="truncate text-sm">{s.name}</div>
                <span className="truncate text-xs text-secondary">
                  {getRelativeTimeString(s.updated_at || "")}
                </span>
              </div>
              <div className="py-3 flex gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
                <Tooltip title="Edit session">
                  <Button
                    type="text"
                    size="small"
                    className="p-1 min-w-[24px] h-6"
                    icon={<Edit className="w-4 h-4" />}
                    onClick={(e) => {
                      e.stopPropagation();
                      onEditSession(s);
                    }}
                  />
                </Tooltip>
                <Tooltip title="Delete session">
                  <Button
                    type="text"
                    size="small"
                    className="p-1 min-w-[24px] h-6"
                    danger
                    icon={<Trash2 className="w-4 h-4 text-red-500" />}
                    onClick={(e) => {
                      e.stopPropagation();
                      if (s.id) onDeleteSession(s.id);
                    }}
                  />
                </Tooltip>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
