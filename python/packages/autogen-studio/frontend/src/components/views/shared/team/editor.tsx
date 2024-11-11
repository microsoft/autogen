import React, { useEffect, useState, useRef } from "react";
import { Modal, Form, message, Button } from "antd";
import { TriangleAlertIcon } from "lucide-react";
import { TeamEditorProps } from "./types";
import type { FormProps } from "antd";
import type { Team, TeamConfig } from "../../../types/datamodel";
import { MonacoEditor } from "../monaco";

const defaultTeamConfig: TeamConfig = {
  name: "",
  participants: [],
  team_type: "RoundRobinGroupChat",
};

type FieldType = {
  config: string;
};

export const TeamEditor: React.FC<TeamEditorProps> = ({
  team,
  onSave,
  onCancel,
  isOpen,
}) => {
  const [form] = Form.useForm();
  const [jsonError, setJsonError] = useState<string | null>(null);
  const editorRef = useRef(null);
  const [editorValue, setEditorValue] = useState<string>("");

  // Set form values when modal opens or team changes
  useEffect(() => {
    if (isOpen) {
      const configStr = team
        ? JSON.stringify(team.config, null, 2)
        : JSON.stringify(defaultTeamConfig, null, 2);
      setEditorValue(configStr);
      form.setFieldsValue({
        config: configStr,
      });
    } else {
      form.resetFields();
      setJsonError(null);
    }
  }, [form, team, isOpen]);

  const validateJSON = (jsonString: string): TeamConfig | null => {
    try {
      const parsed = JSON.parse(jsonString);

      // Basic validation of required fields
      if (typeof parsed.name !== "string" || parsed.name.trim() === "") {
        throw new Error("Team name is required");
      }
      if (!Array.isArray(parsed.participants)) {
        throw new Error("Participants must be an array");
      }
      if (
        !["RoundRobinGroupChat", "SelectorGroupChat"].includes(parsed.team_type)
      ) {
        throw new Error("Invalid team_type");
      }

      return parsed;
    } catch (error) {
      if (error instanceof Error) {
        setJsonError(error.message);
      } else {
        setJsonError("Invalid JSON format");
      }
      return null;
    }
  };

  const onFinish: FormProps<FieldType>["onFinish"] = async () => {
    const config = validateJSON(editorValue);
    if (!config) {
      return;
    }

    try {
      // When updating, keep the existing id and dates
      const teamData: Partial<Team> = team
        ? {
            ...team,
            config,
            // Remove date fields to let the backend handle them
            created_at: undefined,
            updated_at: undefined,
          }
        : { config };

      await onSave(teamData);
      message.success(`Team ${team ? "updated" : "created"} successfully`);
      setJsonError(null);
    } catch (error) {
      if (error instanceof Error) {
        message.error(error.message);
      }
    }
  };

  const handleEditorChange = (value: string) => {
    setEditorValue(value);
    form.setFieldsValue({ config: value });

    // Clear error if JSON becomes valid
    try {
      JSON.parse(value);
      setJsonError(null);
    } catch (e) {
      // Don't set error while typing - Monaco will show syntax errors
    }
  };

  return (
    <Modal
      title={team ? "Edit Team" : "Create Team"}
      open={isOpen}
      onCancel={onCancel}
      footer={null}
      className="text-primary"
      width={800}
      forceRender
    >
      <Form
        form={form}
        name="team-form"
        layout="vertical"
        onFinish={onFinish}
        autoComplete="off"
      >
        <div className="mb-2 text-xs text-gray-500">
          Required fields: name (string), team_type ("RoundRobinGroupChat" |
          "SelectorGroupChat"), participants (array)
        </div>

        <div className="h-[500px] mb-4">
          <MonacoEditor
            value={editorValue}
            onChange={handleEditorChange}
            editorRef={editorRef}
            language="json"
            minimap={false}
          />
        </div>

        {jsonError && (
          <div className="flex items-center gap-1.5 text-sm text-red-500 mb-4">
            <TriangleAlertIcon className="h-4 w-4" />
            <span>{jsonError}</span>
          </div>
        )}

        <Form.Item className="flex justify-end mb-0">
          <div className="flex gap-2">
            <Button onClick={onCancel}>Cancel</Button>
            <Button
              type="primary"
              onClick={() => form.submit()}
              disabled={!!jsonError}
            >
              {team ? "Update" : "Create"}
            </Button>
          </div>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default TeamEditor;
