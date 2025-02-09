import React, { useState, useEffect } from "react";
import { ChevronRight, RotateCcw } from "lucide-react";
import { Switch, Button, Tooltip } from "antd";
import { MessagesSquare } from "lucide-react";
import { useSettingsStore } from "./store";
import { SettingsSidebar } from "./sidebar";
import { SettingsSection } from "./types";
import { LucideIcon } from "lucide-react";

interface SettingToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  description?: string;
}

interface SectionHeaderProps {
  title: string;
  icon: LucideIcon;
  onReset: () => void;
}

const SettingToggle: React.FC<SettingToggleProps> = ({
  checked,
  onChange,
  label,
  description,
}) => (
  <div className="flex justify-between items-start p-4 hover:bg-secondary/5 rounded-lg transition-colors">
    <div className="flex flex-col gap-1">
      <label className="font-medium">{label}</label>
      {description && (
        <span className="text-sm text-secondary">{description}</span>
      )}
    </div>
    <Switch defaultValue={checked} onChange={onChange} />
  </div>
);

const SectionHeader: React.FC<SectionHeaderProps> = ({
  title,
  icon: Icon,
  onReset,
}) => (
  <div className="flex items-center justify-between mb-6">
    <div className="flex items-center gap-2">
      <Icon className="text-accent" size={20} />
      <h2 className="text-lg font-semibold">{title}</h2>
    </div>
    <Tooltip title="Reset section settings">
      <Button
        icon={<RotateCcw className="w-4 h-4" />}
        onClick={onReset}
        type="text"
      />
    </Tooltip>
  </div>
);

export const SettingsManager: React.FC = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("settingsSidebar");
      return stored !== null ? JSON.parse(stored) : true;
    }
    return true;
  });

  const {
    playground,
    updatePlaygroundSettings,
    resetPlaygroundSettings,
    resetAllSettings,
  } = useSettingsStore();

  const sections: SettingsSection[] = [
    {
      id: "playground",
      title: "Playground",
      icon: MessagesSquare,
      content: () => (
        <>
          <SectionHeader
            title="Playground"
            icon={MessagesSquare}
            onReset={resetPlaygroundSettings}
          />
          <div className="space-y-2 rounded-xl border border-secondary">
            <SettingToggle
              checked={playground.showLLMEvents}
              onChange={(checked) =>
                updatePlaygroundSettings({ showLLMEvents: checked })
              }
              label={"Show LLM Events"}
              description="Display detailed LLM call logs in the message thread"
            />
          </div>
        </>
      ),
    },
  ];

  const [currentSection, setCurrentSection] = useState<SettingsSection>(
    sections[0]
  );

  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("settingsSidebar", JSON.stringify(isSidebarOpen));
    }
  }, [isSidebarOpen]);

  return (
    <div className="relative flex h-full w-full">
      <div
        className={`absolute left-0 top-0 h-full transition-all duration-200 ease-in-out ${
          isSidebarOpen ? "w-64" : "w-12"
        }`}
      >
        <SettingsSidebar
          isOpen={isSidebarOpen}
          sections={sections}
          currentSection={currentSection}
          onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
          onSelectSection={setCurrentSection}
        />
      </div>

      <div
        className={`flex-1 transition-all max-w-5xl -mr-6 duration-200 ${
          isSidebarOpen ? "ml-64" : "ml-12"
        }`}
      >
        <div className="p-4 pt-2">
          <div className="flex items-center gap-2 mb-4 text-sm">
            <span className="text-primary font-medium">Settings</span>
            <ChevronRight className="w-4 h-4 text-secondary" />
            <span className="text-secondary">{currentSection.title}</span>
          </div>

          <currentSection.content />

          <div className="mt-12 pt-6 border-t border-secondary flex justify-between items-center">
            <p className="text-xs text-secondary">
              Settings are automatically saved and synced across browser
              sessions
            </p>
            <Button
              type="text"
              danger
              icon={<RotateCcw className="w-4 h-4 mr-1" />}
              onClick={resetAllSettings}
            >
              Reset All Settings
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SettingsManager;
