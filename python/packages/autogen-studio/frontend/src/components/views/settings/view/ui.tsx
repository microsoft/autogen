import React, { useEffect, useState } from "react";
import { Button, Tooltip, message } from "antd";
import { RotateCcw, Save, TriangleAlert } from "lucide-react";
import { settingsAPI } from "../api";
import { Settings, UISettings } from "../../../types/datamodel";
import { useSettingsStore } from "../store";

interface SettingToggleProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  description?: string;
  disabled?: boolean;
}

const SettingToggle: React.FC<SettingToggleProps> = ({
  checked,
  onChange,
  label,
  description,
  disabled = false,
}) => (
  <div className="flex justify-between items-start p-4 hover:bg-secondary/5 rounded transition-colors">
    <div className="flex flex-col gap-1">
      <label className="font-medium">{label}</label>
      {description && (
        <span className="text-sm text-secondary">{description}</span>
      )}
    </div>
    <div className="relative">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
        className="sr-only"
        id={`toggle-${label.replace(/\s+/g, "-").toLowerCase()}`}
      />
      <label
        htmlFor={`toggle-${label.replace(/\s+/g, "-").toLowerCase()}`}
        className={`relative inline-flex items-center h-6 rounded-full w-11 transition-colors focus:outline-none focus:ring-2 focus:ring-accent focus:ring-opacity-50 cursor-pointer ${
          disabled ? "opacity-50 cursor-not-allowed" : ""
        } ${checked ? "bg-accent" : "bg-gray-300"}`}
      >
        <span
          className={`inline-block w-4 h-4 transform bg-white rounded-full transition-transform ${
            checked ? "translate-x-6" : "translate-x-1"
          }`}
        />
      </label>
    </div>
  </div>
);

interface UISettingsPanelProps {
  userId: string;
}

export const UISettingsPanel: React.FC<UISettingsPanelProps> = ({ userId }) => {
  const {
    serverSettings,
    uiSettings: storeUISettings,
    initializeSettings,
  } = useSettingsStore();

  // Local state for UI settings
  const [localUISettings, setLocalUISettings] = useState<UISettings>({
    show_llm_call_events: false,
    expanded_messages_by_default: false,
    show_agent_flow_by_default: false,
  });

  const [isDirty, setIsDirty] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();

  // Initialize local state from store
  useEffect(() => {
    setLocalUISettings(storeUISettings);
  }, [storeUISettings]);

  // Update local state when a setting is changed
  const handleSettingChange = (key: keyof UISettings, value: boolean) => {
    setLocalUISettings((prev) => ({
      ...prev,
      [key]: value,
    }));
    setIsDirty(true);
  };

  // Reset UI settings to defaults
  const handleReset = async () => {
    try {
      setIsSaving(true);

      if (!serverSettings) {
        messageApi.error("Settings not loaded");
        setIsSaving(false);
        return;
      }

      // Define default UI settings
      const DEFAULT_UI_SETTINGS: UISettings = {
        show_llm_call_events: false,
        expanded_messages_by_default: false,
        show_agent_flow_by_default: false,
      };

      // Update local state
      setLocalUISettings(DEFAULT_UI_SETTINGS);

      // Prepare for server update
      const updatedSettings: Settings = {
        ...serverSettings,
        config: {
          ...serverSettings.config,
          ui: DEFAULT_UI_SETTINGS,
        },
        created_at: undefined,
        updated_at: undefined,
      };

      console.log("Updated settings:", updatedSettings);

      // Update on server
      await settingsAPI.updateSettings(updatedSettings, userId);

      // Refresh from server
      await initializeSettings(userId);

      setIsDirty(false);
      messageApi.success("UI settings reset successfully");
    } catch (error) {
      console.error("Failed to reset UI settings:", error);
      messageApi.error("Failed to reset UI settings");
    } finally {
      setIsSaving(false);
    }
  };

  // Save settings to server
  const handleSave = async () => {
    try {
      setIsSaving(true);

      if (!serverSettings) {
        messageApi.error("Settings not loaded");
        setIsSaving(false);
        return;
      }

      // Prepare updated settings
      const updatedSettings: Settings = {
        ...serverSettings,
        config: {
          ...serverSettings.config,
          ui: localUISettings,
        },
        created_at: undefined,
        updated_at: undefined,
      };

      // Update on server
      await settingsAPI.updateSettings(updatedSettings, userId);

      // Refresh from server to ensure sync
      await initializeSettings(userId);

      setIsDirty(false);
      messageApi.success("UI settings saved successfully");
    } catch (error) {
      console.error("Failed to save UI settings:", error);
      messageApi.error("Failed to save UI settings");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className=" ">
      {contextHolder}
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-medium">UI Settings</h3>
        <div className="space-x-2 inline-flex">
          <Tooltip title="Reset to defaults">
            <Button
              icon={<RotateCcw className="w-4 h-4" />}
              onClick={handleReset}
              disabled={isSaving}
            >
              Reset
            </Button>
          </Tooltip>
          <Tooltip title={isDirty ? "Save your changes" : "No unsaved changes"}>
            <Button
              type="primary"
              icon={
                <div className="relative">
                  <Save className="w-4 h-4" />
                  {isDirty && (
                    <div className="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full" />
                  )}
                </div>
              }
              onClick={handleSave}
              disabled={!isDirty || isSaving}
              loading={isSaving}
            >
              Save
            </Button>
          </Tooltip>
        </div>
      </div>

      <div className="space-y-0 rounded border border-secondary">
        <SettingToggle
          checked={localUISettings.show_llm_call_events}
          onChange={(checked) =>
            handleSettingChange("show_llm_call_events", checked)
          }
          label="Show LLM Events"
          description="Display detailed LLM call logs in the message thread"
          disabled={isSaving}
        />

        <SettingToggle
          checked={localUISettings.expanded_messages_by_default ?? false}
          onChange={(checked) =>
            handleSettingChange("expanded_messages_by_default", checked)
          }
          label="Expand Messages by Default"
          description="Automatically expand message threads when they load"
          disabled={isSaving}
        />

        <SettingToggle
          checked={localUISettings.show_agent_flow_by_default ?? false}
          onChange={(checked) =>
            handleSettingChange("show_agent_flow_by_default", checked)
          }
          label="Show Agent Flow by Default"
          description="Display the agent flow diagram automatically"
          disabled={isSaving}
        />
      </div>

      <div className="mt-4 hidden text-xs text-secondary">
        <TriangleAlert
          strokeWidth={1.5}
          className="inline-block mr-1 h-4 w-4"
        />{" "}
        These settings are automatically saved and synced across browser
        sessions
      </div>
    </div>
  );
};

export default UISettingsPanel;
