import React, { useContext, useEffect, useState } from "react";
import { Modal, Form, message, Input, Button, Select, Spin } from "antd";
import { TriangleAlertIcon } from "lucide-react";
import type { FormProps } from "antd";
import { SessionEditorProps } from "./types";
import { Team } from "../../types/datamodel";
import { teamAPI } from "../team/api";
import { appContext } from "../../../hooks/provider";
import { Link } from "gatsby";

type FieldType = {
  name: string;
  team_id?: number;
};

export const SessionEditor: React.FC<SessionEditorProps> = ({
  session,
  onSave,
  onCancel,
  isOpen,
}) => {
  const [form] = Form.useForm();
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(false);
  const { user } = useContext(appContext);
  const [messageApi, contextHolder] = message.useMessage();

  // Fetch teams when modal opens
  useEffect(() => {
    const fetchTeams = async () => {
      if (isOpen) {
        try {
          setLoading(true);
          const userId = user?.email || "";
          const teamsData = await teamAPI.listTeams(userId);
          setTeams(teamsData);
        } catch (error) {
          messageApi.error("Error loading teams");
          console.error("Error loading teams:", error);
        } finally {
          setLoading(false);
        }
      }
    };

    fetchTeams();
  }, [isOpen, user?.email]);

  // Set form values when modal opens or session changes
  useEffect(() => {
    if (isOpen) {
      form.setFieldsValue({
        name: session?.name || "",
        team_id: session?.team_id || undefined,
      });
    } else {
      form.resetFields();
    }
  }, [form, session, isOpen]);

  const onFinish: FormProps<FieldType>["onFinish"] = async (values) => {
    try {
      await onSave({
        ...values,
        id: session?.id,
      });
      messageApi.success(
        `Session ${session ? "updated" : "created"} successfully`
      );
    } catch (error) {
      if (error instanceof Error) {
        messageApi.error(error.message);
      }
    }
  };

  const onFinishFailed: FormProps<FieldType>["onFinishFailed"] = (
    errorInfo
  ) => {
    messageApi.error("Please check the form for errors");
    console.error("Form validation failed:", errorInfo);
  };

  const hasNoTeams = !loading && teams.length === 0;

  return (
    <Modal
      title={session ? "Edit Session" : "Create Session"}
      open={isOpen}
      onCancel={onCancel}
      footer={null}
      className="text-primary"
      forceRender
    >
      {contextHolder}
      <Form
        form={form}
        name="session-form"
        layout="vertical"
        onFinish={onFinish}
        onFinishFailed={onFinishFailed}
        autoComplete="off"
      >
        <Form.Item<FieldType>
          label="Session Name"
          name="name"
          rules={[
            { required: true, message: "Please enter a session name" },
            { max: 100, message: "Session name cannot exceed 100 characters" },
          ]}
        >
          <Input />
        </Form.Item>

        <div className="space-y-2   w-full">
          <Form.Item<FieldType>
            className="w-full"
            label="Team"
            name="team_id"
            rules={[{ required: true, message: "Please select a team" }]}
          >
            <Select
              placeholder="Select a team"
              loading={loading}
              disabled={loading || hasNoTeams}
              showSearch
              optionFilterProp="children"
              filterOption={(input, option) =>
                (option?.label ?? "")
                  .toLowerCase()
                  .includes(input.toLowerCase())
              }
              options={teams.map((team) => ({
                value: team.id,
                label: `${team.config.name} (${team.config.team_type})`,
              }))}
              notFoundContent={loading ? <Spin size="small" /> : null}
            />
          </Form.Item>
        </div>

        <div className="text-sm text-accent ">
          <Link to="/build">view all teams</Link>
        </div>

        {hasNoTeams && (
          <div className="flex border p-1 rounded -mt-2 mb-4 items-center gap-1.5 text-sm text-yellow-600">
            <TriangleAlertIcon className="h-4 w-4" />
            <span>No teams found. Please create a team first.</span>
          </div>
        )}

        <Form.Item className="flex justify-end mb-0">
          <div className="flex gap-2">
            <Button onClick={onCancel}>Cancel</Button>
            <Button type="primary" htmlType="submit" disabled={hasNoTeams}>
              {session ? "Update" : "Create"}
            </Button>
          </div>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default SessionEditor;
