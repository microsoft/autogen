import React, { useContext, useEffect, useRef, useState } from "react";
import type { BaseSelectRef } from "rc-select";
import {
  Button,
  Form,
  Input,
  Select,
  Table,
  message,
  Tooltip,
  Card,
} from "antd";
import type { FormInstance, InputRef } from "antd";
import { Plus, Trash2, Save, Edit, TriangleAlert } from "lucide-react";
import { settingsAPI } from "../api";
import {
  Settings as SettingsType,
  EnvironmentVariable,
  EnvironmentVariableType,
} from "../../../types/datamodel";

// Create a form context
const EditableContext = React.createContext<FormInstance | null>(null);

// Define item type for table data
interface EnvVariableItem {
  key: string;
  name: string;
  value: string;
  type: EnvironmentVariableType;
}

// Define editable row props
interface EditableRowProps {
  index: number;
}

// Component for editable rows
const EditableRow: React.FC<EditableRowProps> = ({ index, ...props }) => {
  const [form] = Form.useForm();
  return (
    <Form form={form} component={false}>
      <EditableContext.Provider value={form}>
        <tr {...props} />
      </EditableContext.Provider>
    </Form>
  );
};

// Define editable cell props
interface EditableCellProps {
  title: React.ReactNode;
  editable: boolean;
  children: React.ReactNode;
  dataIndex: keyof EnvVariableItem;
  record: EnvVariableItem;
  handleSave: (record: EnvVariableItem) => void;
  inputType: "text" | "password" | "select";
  options?: { value: string; label: string }[];
}

// Component for editable cells
const EditableCell: React.FC<EditableCellProps> = ({
  title,
  editable,
  children,
  dataIndex,
  record,
  handleSave,
  inputType,
  options,
  ...restProps
}) => {
  const [editing, setEditing] = useState(false);
  const inputRef = useRef<InputRef>(null);
  const selectRef = useRef<BaseSelectRef>(null);
  const form = useContext(EditableContext)!;

  useEffect(() => {
    if (editing) {
      if (inputType === "select") {
        selectRef.current?.focus();
      } else {
        inputRef.current?.focus();
      }
    }
  }, [editing, inputType]);

  const toggleEdit = () => {
    setEditing(!editing);
    form.setFieldsValue({ [dataIndex]: record[dataIndex] });
  };

  const save = async () => {
    try {
      const values = await form.validateFields();
      toggleEdit();
      handleSave({ ...record, ...values });
    } catch (errInfo) {
      console.log("Save failed:", errInfo);
    }
  };

  let childNode = children;

  if (editable) {
    childNode = editing ? (
      <Form.Item
        style={{ margin: 0 }}
        name={dataIndex}
        rules={
          dataIndex === "name"
            ? [{ required: true, message: `${title} is required.` }]
            : []
        }
      >
        {inputType === "text" ? (
          <Input ref={inputRef} onPressEnter={save} onBlur={save} />
        ) : inputType === "select" ? (
          <Select
            ref={selectRef}
            options={options}
            onBlur={save}
            onChange={() => setTimeout(save, 100)}
            open={editing}
            style={{ width: "100%" }}
          />
        ) : inputType === "password" ? (
          <Input.Password
            ref={inputRef}
            onPressEnter={save}
            onBlur={save}
            visibilityToggle
          />
        ) : (
          <Input ref={inputRef} onPressEnter={save} onBlur={save} />
        )}
      </Form.Item>
    ) : (
      <div
        className="editable-cell-value-wrap group cursor-pointer"
        style={{ paddingRight: 24, minHeight: 20 }}
        onClick={toggleEdit}
      >
        <div className="flex items-center">
          <span className="flex-grow">
            {inputType === "password"
              ? "••••••••"
              : inputType === "select" && options
              ? options.find((opt) => opt.value === children)?.label || children
              : children || " "}
          </span>
          <Edit className="w-3 h-3 text-gray-400 opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
      </div>
    );
  }

  return <td {...restProps}>{childNode}</td>;
};

type ColumnTypes = {
  title: string;
  dataIndex: string;
  width?: string;
  editable?: boolean;
  inputType?: "text" | "password" | "select";
  options?: { value: string; label: string }[];
  render?: (text: any, record: EnvVariableItem) => React.ReactNode;
};

interface EnvironmentVariablesPanelProps {
  serverSettings: SettingsType | null;
  loading: boolean;
  userId: string;
  initializeSettings: (userId: string) => Promise<void>;
}

export const EnvironmentVariablesPanel: React.FC<
  EnvironmentVariablesPanelProps
> = ({ serverSettings, loading, userId, initializeSettings }) => {
  const [dataSource, setDataSource] = useState<EnvVariableItem[]>([]);
  const [isDirty, setIsDirty] = useState(false);
  const [messageApi, contextHolder] = message.useMessage();

  // Update local state when serverSettings change
  useEffect(() => {
    if (serverSettings) {
      // Transform environment variables into table data
      const tableData = serverSettings.config.environment.map((env, index) => ({
        key: `${index}`,
        name: env.name,
        value: env.value,
        type: env.type,
      }));

      setDataSource(tableData);
      setIsDirty(false);
    }
  }, [serverSettings]);

  // Save settings to API
  const handleSave = async () => {
    try {
      // Transform table data back to environment variables
      const environment: EnvironmentVariable[] = dataSource.map((item) => ({
        name: item.name,
        value: item.value,
        type: item.type,
        required: false, // Setting required to false for all items
      }));

      // Only update if we have serverSettings
      if (!serverSettings) {
        messageApi.error("Settings not loaded yet");
        return;
      }

      const updatedSettings: SettingsType = {
        ...serverSettings,
        config: {
          ...serverSettings.config,
          environment,
        },
      };

      const sanitizedSettings = {
        id: updatedSettings.id,
        config: updatedSettings.config,
        user_id: userId,
      };

      await settingsAPI.updateSettings(sanitizedSettings, userId);

      // Refresh settings from server to ensure everything is in sync
      await initializeSettings(userId);

      setIsDirty(false);
      messageApi.success("Environment variables saved successfully");
    } catch (error) {
      console.error("Failed to save settings:", error);
      messageApi.error("Failed to save environment variables");
    }
  };

  // Handle adding a new variable
  const handleAdd = async () => {
    const newVariable: EnvVariableItem = {
      key: `${dataSource.length + 1}`,
      name: "",
      value: "",
      type: "string",
    };

    const newDataSource = [...dataSource, newVariable];
    setDataSource(newDataSource);

    // No auto-save for add since the name field will be empty
    // Just mark as dirty so user can edit and then save
    setIsDirty(true);
  };

  // Handle deleting a variable and auto-save
  const handleDelete = async (key: string) => {
    const newDataSource = dataSource.filter((item) => item.key !== key);
    setDataSource(newDataSource);
    setIsDirty(true);
  };

  // Handle saving a cell edit
  const handleCellSave = async (row: EnvVariableItem) => {
    const newData = [...dataSource];
    const index = newData.findIndex((item) => row.key === item.key);
    const item = newData[index];
    newData.splice(index, 1, { ...item, ...row });
    setDataSource(newData);
    setIsDirty(true);
  };

  // Environment variable types for select options
  const ENVIRONMENT_VARIABLE_TYPES: EnvironmentVariableType[] = [
    "string",
    "number",
    "boolean",
    "secret",
  ];

  const typeOptions = ENVIRONMENT_VARIABLE_TYPES.map((type) => ({
    value: type,
    label: type.charAt(0).toUpperCase() + type.slice(1),
  }));

  // Define columns
  const columns: ColumnTypes[] = [
    {
      title: "Name",
      dataIndex: "name",
      width: "55%",
      editable: true,
      inputType: "text",
    },
    {
      title: "Value",
      dataIndex: "value",
      width: "45%",
      editable: true,
      inputType: "password",
    },
    {
      title: "Actions",
      dataIndex: "operation",
      render: (_, record) => (
        <Tooltip title="Delete variable">
          <Button
            type="text"
            danger
            icon={<Trash2 className="w-4 h-4" />}
            onClick={() => handleDelete(record.key)}
          />
        </Tooltip>
      ),
    },
  ];

  // Map columns to include cell properties
  const mergedColumns = columns.map((col) => {
    if (!col.editable) {
      return col;
    }
    return {
      ...col,
      onCell: (record: EnvVariableItem) => ({
        record,
        editable: col.editable,
        dataIndex: col.dataIndex,
        title: col.title,
        inputType: col.inputType,
        options: col.options,
        handleSave: handleCellSave,
      }),
    };
  });

  // Define custom table components
  const components = {
    body: {
      row: EditableRow,
      cell: EditableCell,
    },
  };

  return (
    <Card className="shadow-sm">
      {contextHolder}
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-medium">Environment Variables</h3>
        <div className="space-x-2 inline-flex">
          <Tooltip title="Add new variable">
            <Button
              type="default"
              icon={<Plus className="w-4 h-4" />}
              onClick={handleAdd}
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
              onClick={handleSave}
              disabled={!isDirty}
            >
              Save
            </Button>
          </Tooltip>
        </div>
      </div>

      <Table
        components={components}
        rowClassName={() => "editable-row"}
        bordered
        dataSource={dataSource}
        columns={mergedColumns as any}
        pagination={false}
        loading={loading}
      />

      <div className="mt-6 pt-4 border-t border-secondary">
        <p className="text-xs text-secondary">
          <TriangleAlert
            strokeWidth={1.5}
            className="inline-block mr-1 h-4 w-4"
          />{" "}
          Note: Environment variables are currently available to all processes
          on the server.
        </p>
      </div>
    </Card>
  );
};
