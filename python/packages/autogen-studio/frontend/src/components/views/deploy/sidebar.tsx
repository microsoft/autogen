import React from "react";
import { Button, Tooltip } from "antd";
import {
  PanelLeftClose,
  PanelLeftOpen,
  Book,
  InfoIcon,
  RefreshCcw,
} from "lucide-react";
import type { Guide } from "./types";

interface DeploySidebarProps {
  isOpen: boolean;
  guides: Guide[];
  currentGuide: Guide | null;
  onToggle: () => void;
  onSelectGuide: (guide: Guide) => void;
  isLoading?: boolean;
}

export const DeploySidebar: React.FC<DeploySidebarProps> = ({
  isOpen,
  guides,
  currentGuide,
  onToggle,
  onSelectGuide,
  isLoading = false,
}) => {
  // Render collapsed state
  if (!isOpen) {
    return (
      <div className="h-full border-r border-secondary">
        <div className="p-2 -ml-2">
          <Tooltip title="Documentation">
            <button
              onClick={onToggle}
              className="p-2 rounded-md hover:bg-secondary hover:text-accent text-secondary transition-colors focus:outline-none focus:ring-2 focus:ring-accent focus:ring-opacity-50"
            >
              <PanelLeftOpen strokeWidth={1.5} className="h-6 w-6" />
            </button>
          </Tooltip>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full border-r border-secondary">
      {/* Header */}
      <div className="flex items-center justify-between pt-0 p-4 pl-2 pr-2 border-b border-secondary">
        <div className="flex items-center gap-2">
          {/* <Book className="w-4 h-4" /> */}
          <span className="text-primary font-medium">Guides</span>
          {/* <span className="px-2 py-0.5 text-xs bg-accent/10 text-accent rounded">
            {guides.length}
          </span> */}
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

      {/* Loading State */}
      {isLoading && (
        <div className="p-4">
          <RefreshCcw className="w-4 h-4 inline-block animate-spin" />
        </div>
      )}

      {/* Empty State */}
      {!isLoading && guides.length === 0 && (
        <div className="p-2 m-2 text-center text-secondary text-sm border border-dashed rounded">
          <InfoIcon className="w-4 h-4 inline-block mr-1.5 -mt-0.5" />
          No deployment guide available
        </div>
      )}

      {/* Guides List */}
      <div className="overflow-y-auto h-[calc(100%-64px)] mt-4">
        {guides.map((guide) => (
          <div key={guide.id} className="relative">
            <div
              className={`absolute top-1 left-0.5 z-50 h-[calc(100%-8px)]
               w-1 bg-opacity-80 rounded ${
                 currentGuide?.id === guide.id ? "bg-accent" : "bg-tertiary"
               }`}
            />
            <div
              className={`group ml-1 flex flex-col p-2 rounded-l cursor-pointer hover:bg-secondary ${
                currentGuide?.id === guide.id
                  ? "border-accent bg-secondary"
                  : "border-transparent"
              }`}
              onClick={() => onSelectGuide(guide)}
            >
              {/* Guide Title */}
              <div className="flex items-center justify-between">
                <span className="text-sm truncate">{guide.title}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
