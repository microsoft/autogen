import React, { useState, useEffect, useContext } from "react";
import { Button, Input, Select, Table, Switch, message, Tooltip } from "antd";
import { Plus, Trash2, Save } from "lucide-react";
import { appContext } from "../../../hooks/provider";
import { settingsAPI } from "./api";
import {
  Settings,
  EnvironmentVariable,
  EnvironmentVariableType,
} from "../../types/datamodel";

const DEFAULT_SETTINGS: Settings = {
  config: {
    environment: [],
  },
};

export const EnvironmentVariables: React.FC = () => {
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);
  const [loading, setLoading] = useState(true);
  const [isDirty, setIsDirty] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();

  const { user } = useContext(appContext);
  const userId = user?.email || "";

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      setLoading(true);
      const data = await settingsAPI.getSettings(userId);
      setSettings(data);
      setIsDirty(false);
    } catch (error) {
      console.error("Failed to load settings:", error);
      setSettings(DEFAULT_SETTINGS);
      messageApi.error("Failed to load environment variables");
    } finally {
      setLoading(false);
    }
  };

  const handleAddVariable = () => {
    const newVar: EnvironmentVariable = {
      name: "",
      value: "",
      type: "string",
      required: false,
    };

    const newSettings = {
      ...settings,
      config: {
        ...settings.config,
        environment: [...settings.config.environment, newVar],
      },
    };

    setSettings(newSettings);
    handleSave(newSettings);
  };

  const handleSave = async (settingsToSave: Settings) => {
    try {
      const sanitizedSettings = {
        id: settingsToSave.id,
        config: settingsToSave.config,
        user_id: userId,
      };
      await settingsAPI.updateSettings(sanitizedSettings, userId);
      setIsDirty(false);
      messageApi.success("Environment variables saved successfully");
    } catch (error) {
      console.error("Failed to save settings:", error);
      messageApi.error("Failed to save environment variables");
    }
  };

  const updateEnvironmentVariable = (
    index: number,
    updates: Partial<EnvironmentVariable>
  ) => {
    const newEnv = [...settings.config.environment];
    newEnv[index] = { ...newEnv[index], ...updates };
    setSettings({
      ...settings,
      config: { ...settings.config, environment: newEnv },
    });
    setIsDirty(true);
  };

  const ENVIRONMENT_VARIABLE_TYPES: EnvironmentVariableType[] = [
    "string",
    "number",
    "boolean",
    "secret",
  ];

  const columns = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      render: (text: string, _: EnvironmentVariable, index: number) => (
        <Input
          value={text}
          placeholder="Variable name"
          onChange={(e) =>
            updateEnvironmentVariable(index, { name: e.target.value })
          }
        />
      ),
    },
    {
      title: "Value",
      dataIndex: "value",
      key: "value",
      render: (_: string, record: EnvironmentVariable, index: number) => (
        <Input.Password
          value={record.value}
          placeholder="Variable value"
          onChange={(e) =>
            updateEnvironmentVariable(index, { value: e.target.value })
          }
          visibilityToggle
        />
      ),
    },
    {
      title: "Type",
      dataIndex: "type",
      key: "type",
      render: (text: string, _: EnvironmentVariable, index: number) => (
        <Select<EnvironmentVariableType>
          value={text as EnvironmentVariableType}
          style={{ width: 120 }}
          onChange={(value) =>
            updateEnvironmentVariable(index, { type: value })
          }
          options={ENVIRONMENT_VARIABLE_TYPES.map((type) => ({
            value: type,
            label: type.charAt(0).toUpperCase() + type.slice(1),
          }))}
        />
      ),
    },
    {
      title: "Required",
      dataIndex: "required",
      key: "required",
      render: (value: boolean, _: EnvironmentVariable, index: number) => (
        <Tooltip title={value ? "Mark as optional" : "Mark as required"}>
          <Switch
            checked={value}
            onChange={(checked) =>
              updateEnvironmentVariable(index, { required: checked })
            }
          />
        </Tooltip>
      ),
    },
    {
      title: "Actions",
      key: "actions",
      render: (_: any, __: any, index: number) => (
        <Tooltip title="Delete variable">
          <Button
            type="text"
            danger
            icon={<Trash2 className="w-4 h-4" />}
            onClick={() => {
              const newEnv = [...settings.config.environment];
              newEnv.splice(index, 1);
              setSettings({
                ...settings,
                config: { ...settings.config, environment: newEnv },
              });
              setIsDirty(true);
              // save
              handleSave({
                ...settings,
                config: { ...settings.config, environment: newEnv },
              });
            }}
          />
        </Tooltip>
      ),
    },
  ];

  return (
    <div className="space-y-4">
      {contextHolder}
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium"> </h3>
        <div className="space-x-2 inline-flex">
          <Tooltip title="Add new variable">
            <Button
              type="primary"
              icon={<Plus className="w-4 h-4" />}
              onClick={handleAddVariable}
            >
              Add
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
              onClick={() => handleSave(settings)}
            >
              Save
            </Button>
          </Tooltip>
        </div>
      </div>
      <Table
        loading={loading}
        dataSource={settings.config.environment}
        columns={columns}
        rowKey={(record) => record.name + record.value}
        pagination={false}
      />
    </div>
  );
};

export default EnvironmentVariables;
