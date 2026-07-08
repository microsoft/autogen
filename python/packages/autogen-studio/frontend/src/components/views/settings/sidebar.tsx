import React from "react";
import { Button, Tooltip } from "antd";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { SettingsSection } from "./types";

interface SettingsSidebarProps {
  isOpen: boolean;
  sections: SettingsSection[];
  currentSection: SettingsSection;
  onToggle: () => void;
  onSelectSection: (section: SettingsSection) => void;
}

export const SettingsSidebar: React.FC<SettingsSidebarProps> = ({
  isOpen,
  sections,
  currentSection,
  onToggle,
  onSelectSection,
}) => {
  // Render collapsed state
  if (!isOpen) {
    return (
      <div className="h-full border-r border-secondary">
        <div className="p-2 -ml-2">
          <Tooltip title={`Settings (${sections.length})`}>
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
          <span className="text-primary font-medium">Settings</span>
          <span className="px-2 py-0.5 text-xs bg-accent/10 text-accent rounded">
            {sections.length}
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

      <div className="overflow-y-auto h-[calc(100%-64px)]">
        {sections.map((section) => (
          <div key={section.id} className="relative">
            <div
              className={`absolute top-1 left-0.5 z-50 h-[calc(100%-8px)] w-1 bg-opacity-80 rounded 
                ${
                  currentSection.id === section.id ? "bg-accent" : "bg-tertiary"
                }`}
            />
            <div
              className={`group ml-1 flex flex-col p-3 rounded-l cursor-pointer hover:bg-secondary 
                ${
                  currentSection.id === section.id
                    ? "border-accent bg-secondary"
                    : "border-transparent"
                }`}
              onClick={() => onSelectSection(section)}
            >
              <div className="flex items-center gap-2">
                <section.icon className="w-4 h-4" />
                <span className="text-sm">{section.title}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
