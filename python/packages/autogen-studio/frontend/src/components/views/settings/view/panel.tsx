import React, { useContext, useEffect, useState } from "react";
import { message, Card } from "antd";
import { appContext } from "../../../../hooks/provider";
import { settingsAPI } from "../api";
import {
  Component,
  ComponentConfig,
  ModelConfig,
  Settings as SettingsType,
  EnvironmentVariable,
} from "../../../types/datamodel";
import { useSettingsStore } from "../store";
import { EnvironmentVariablesPanel } from "./environment";
import { ModelConfigPanel } from "./modelconfig";

const DEFAULT_SETTINGS: SettingsType = {
  config: {
    environment: [],
    ui: {
      show_llm_call_events: false,
      expanded_messages_by_default: false,
      show_agent_flow_by_default: false,
    },
  },
};

export const SettingsPanel: React.FC = () => {
  //   const [loading, setLoading] = useState(true);
  const [messageApi, contextHolder] = message.useMessage();
  const [isModelEditorOpen, setIsModelEditorOpen] = useState(false);

  const { user } = useContext(appContext);
  const userId = user?.email || "";

  // Get settings from the store
  const { serverSettings, initializeSettings } = useSettingsStore();

  // Initialize settings once on component mount
  //   useEffect(() => {
  //     if (userId) {
  //       setLoading(true);
  //       initializeSettings(userId)
  //         .catch((error) => {
  //           console.error("Failed to initialize settings:", error);
  //           messageApi.error("Failed to load settings");
  //         })
  //         .finally(() => {
  //           setLoading(false);
  //         });
  //     }
  //   }, [userId]); // Removed initializeSettings from dependencies

  // Function to create a default model client if none exists
  const createDefaultModelClient = (): Component<ModelConfig> => {
    return {
      provider: "openai",
      component_type: "model",
      label: "Default Model Client",
      description: "Default model client for this environment",
      config: {
        model: "gpt-3.5-turbo",
        temperature: 0.7,
        max_tokens: 1000,
      },
    };
  };

  // Handle updating the default model client
  const handleModelUpdate = async (
    updatedModel: Component<ComponentConfig>
  ) => {
    try {
      if (!serverSettings) {
        messageApi.error("Settings not loaded yet");
        return;
      }

      const updatedSettings: SettingsType = {
        ...serverSettings,
        config: {
          ...serverSettings.config,
          default_model_client: updatedModel as Component<ModelConfig>,
        },
      };

      const sanitizedSettings = {
        id: updatedSettings.id,
        config: updatedSettings.config,
        user_id: userId,
      };

      await settingsAPI.updateSettings(sanitizedSettings, userId);

      // Refresh settings from server
      await initializeSettings(userId);

      messageApi.success("Default model client updated successfully");
      setIsModelEditorOpen(false);
    } catch (error) {
      console.error("Failed to update default model client:", error);
      messageApi.error("Failed to update default model client");
    }
  };

  // Get the model component to edit
  const modelComponent = serverSettings?.config.default_model_client
    ? serverSettings.config.default_model_client
    : createDefaultModelClient();

  return (
    <div className="settings-panel space-y-8">
      {contextHolder}

      {/* Model Configuration Panel */}
      <ModelConfigPanel
        modelComponent={modelComponent}
        onModelUpdate={handleModelUpdate}
      />

      {/* Environment Variables Panel */}
      <EnvironmentVariablesPanel
        serverSettings={serverSettings}
        loading={false}
        userId={userId}
        initializeSettings={initializeSettings}
      />
    </div>
  );
};

export default SettingsPanel;
