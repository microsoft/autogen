import React from "react";
import { Button, Tooltip } from "antd";
import {
  Plus,
  Edit,
  Trash2,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react";
import type { Session } from "../../types/datamodel";
import { getRelativeTimeString } from "../atoms";

interface SidebarProps {
  isOpen: boolean;
  sessions: Session[];
  currentSession: Session | null;
  onToggle: () => void;
  onSelectSession: (session: Session) => void;
  onEditSession: (session?: Session) => void;
  onDeleteSession: (sessionId: number) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  sessions,
  currentSession,
  onToggle,
  onSelectSession,
  onEditSession,
  onDeleteSession,
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
        <div className=" mr-2 w-full">
          <Tooltip title="Create new session">
            <Button
              type="primary"
              className="w-full"
              icon={<Plus className="w-4 h-4" />}
              onClick={() => onEditSession()}
            >
              New Session
            </Button>
          </Tooltip>
        </div>
      </div>

      <div className="py-2 flex text-sm text-secondary">Recents</div>

      {/* no sessions found */}

      {sessions.length === 0 && (
        <div className="mb-2 text-xs text-secondary">No sessions found</div>
      )}

      <div className="overflow-y-auto   h-[calc(100%-150px)]">
        {sessions.map((s) => (
          <div
            key={s.id}
            className={`group flex items-center justify-between p-2 py-1 text-sm cursor-pointer hover:bg-tertiary ${
              currentSession?.id === s.id
                ? "border-l-2 border-accent bg-tertiary"
                : ""
            }`}
            onClick={() => onSelectSession(s)}
          >
            <span className="truncate text-sm flex-1">{s.name}</span>
            <span className="ml-2 truncate text-xs text-secondary flex-1">
              {getRelativeTimeString(s.updated_at || "")}
            </span>
            <div className="flex gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
              <Tooltip title="Edit session">
                <Button
                  type="text"
                  size="small"
                  className="p-0 min-w-[24px] h-6"
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
                  className="p-0 min-w-[24px] h-6"
                  danger
                  icon={<Trash2 className="w-4 h-4  text-red-500" />}
                  onClick={(e) => {
                    e.stopPropagation();
                    if (s.id) onDeleteSession(s.id);
                  }}
                />
              </Tooltip>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
