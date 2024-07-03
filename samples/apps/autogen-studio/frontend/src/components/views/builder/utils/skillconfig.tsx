import React from "react";
import { fetchJSON, getServerUrl, sampleModelConfig } from "../../../utils";
import { Button, Input, message, theme } from "antd";
import {
  CpuChipIcon,
  EyeIcon,
  EyeSlashIcon,
  InformationCircleIcon,
  PlusIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import { ISkill, IStatus } from "../../../types";
import { Card, ControlRowView, MonacoEditor } from "../../../atoms";
import TextArea from "antd/es/input/TextArea";
import { appContext } from "../../../../hooks/provider";

const SecretsEditor = ({
  secrets = [],
  updateSkillConfig,
}: {
  secrets: { secret: string; value: string }[];
  updateSkillConfig: (key: string, value: any) => void;
}) => {
  const [editingIndex, setEditingIndex] = React.useState<number | null>(null);
  const [newSecret, setNewSecret] = React.useState<string>("");
  const [newValue, setNewValue] = React.useState<string>("");

  const toggleEditing = (index: number) => {
    setEditingIndex(editingIndex === index ? null : index);
  };

  const handleAddSecret = () => {
    if (newSecret && newValue) {
      const updatedSecrets = [
        ...secrets,
        { secret: newSecret, value: newValue },
      ];
      updateSkillConfig("secrets", updatedSecrets);
      setNewSecret("");
      setNewValue("");
    }
  };

  const handleRemoveSecret = (index: number) => {
    const updatedSecrets = secrets.filter((_, i) => i !== index);
    updateSkillConfig("secrets", updatedSecrets);
  };

  const handleSecretChange = (index: number, key: string, value: string) => {
    const updatedSecrets = secrets.map((item, i) =>
      i === index ? { ...item, [key]: value } : item
    );
    updateSkillConfig("secrets", updatedSecrets);
  };

  return (
    <div className="mt-4">
      {secrets && (
        <div className="flex flex-col gap-2">
          {secrets.map((secret, index) => (
            <div key={index} className="flex items-center gap-2">
              <Input
                value={secret.secret}
                disabled={editingIndex !== index}
                onChange={(e) =>
                  handleSecretChange(index, "secret", e.target.value)
                }
                className="flex-1"
              />
              <Input.Password
                value={secret.value}
                visibilityToggle
                disabled={editingIndex !== index}
                onChange={(e) =>
                  handleSecretChange(index, "value", e.target.value)
                }
                className="flex-1"
              />
              <Button
                icon={
                  editingIndex === index ? (
                    <EyeSlashIcon className="h-5 w-5" />
                  ) : (
                    <EyeIcon className="h-5 w-5" />
                  )
                }
                onClick={() => toggleEditing(index)}
              />
              <Button
                icon={<TrashIcon className="h-5 w-5" />}
                onClick={() => handleRemoveSecret(index)}
              />
            </div>
          ))}
        </div>
      )}
      <div className="flex items-center gap-2 mt-2">
        <Input
          placeholder="New Secret"
          value={newSecret}
          onChange={(e) => setNewSecret(e.target.value)}
          className="flex-1"
        />
        <Input.Password
          placeholder="New Value"
          value={newValue}
          onChange={(e) => setNewValue(e.target.value)}
          className="flex-1"
        />
        <Button
          icon={<PlusIcon className="h-5 w-5" />}
          onClick={handleAddSecret}
        />
      </div>
    </div>
  );
};

export const SkillConfigView = ({
  skill,
  setSkill,
  close,
}: {
  skill: ISkill;
  setSkill: (newModel: ISkill) => void;
  close: () => void;
}) => {
  const [loading, setLoading] = React.useState(false);

  const serverUrl = getServerUrl();
  const { user } = React.useContext(appContext);
  const testModelUrl = `${serverUrl}/skills/test`;
  const createSkillUrl = `${serverUrl}/skills`;

  const createSkill = (skill: ISkill) => {
    setLoading(true);
    skill.user_id = user?.email;
    const payLoad = {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(skill),
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        setSkill(data.data);
      } else {
        message.error(data.message);
      }
      setLoading(false);
    };
    const onError = (err: any) => {
      message.error(err.message);
      setLoading(false);
    };
    const onFinal = () => {
      setLoading(false);
      setControlChanged(false);
    };
    fetchJSON(createSkillUrl, payLoad, onSuccess, onError, onFinal);
  };

  const [controlChanged, setControlChanged] = React.useState<boolean>(false);

  const updateSkillConfig = (key: string, value: string) => {
    if (skill) {
      const updatedSkill = { ...skill, [key]: value };
      //   setSkill(updatedModelConfig);
      setSkill(updatedSkill);
    }
    setControlChanged(true);
  };

  const hasChanged = !controlChanged && skill.id !== undefined;
  const editorRef = React.useRef<any | null>(null);

  return (
    <div className="relative ">
      {skill && (
        <div style={{ minHeight: "65vh" }}>
          <div className="flex gap-3">
            <div className="h-ful flex-1 ">
              <div className="mb-2 h-full" style={{ minHeight: "65vh" }}>
                <div className="h-full mt-2" style={{ height: "65vh" }}>
                  <MonacoEditor
                    value={skill?.content}
                    language="python"
                    editorRef={editorRef}
                    onChange={(value: string) => {
                      updateSkillConfig("content", value);
                    }}
                  />
                </div>
              </div>
            </div>
            <div className="w-72 ">
              <div className="">
                <ControlRowView
                  title="Name"
                  className=""
                  description="Skill name, should match function name"
                  value={skill?.name || ""}
                  control={
                    <Input
                      className="mt-2 w-full"
                      value={skill?.name}
                      onChange={(e) => {
                        updateSkillConfig("name", e.target.value);
                      }}
                    />
                  }
                />

                <ControlRowView
                  title="Description"
                  className="mt-4"
                  description="Description of the skill"
                  value={skill?.description || ""}
                  control={
                    <TextArea
                      className="mt-2 w-full"
                      value={skill?.description}
                      onChange={(e) => {
                        updateSkillConfig("description", e.target.value);
                      }}
                    />
                  }
                />

                <ControlRowView
                  title="Secrets"
                  className="mt-4"
                  description="Environment variables"
                  value=""
                  control={
                    <SecretsEditor
                      secrets={skill?.secrets || []}
                      updateSkillConfig={updateSkillConfig}
                    />
                  }
                />
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="w-full mt-4 text-right">
        {/* <Button
          key="test"
          type="primary"
          loading={loading}
          onClick={() => {
            if (skill) {
              testModel(skill);
            }
          }}
        >
          Test Model
        </Button> */}

        {!hasChanged && (
          <Button
            className="ml-2"
            key="save"
            type="primary"
            onClick={() => {
              if (skill) {
                createSkill(skill);
                setSkill(skill);
              }
            }}
          >
            {skill?.id ? "Update Skill" : "Save Skill"}
          </Button>
        )}

        <Button
          className="ml-2"
          key="close"
          type="default"
          onClick={() => {
            close();
          }}
        >
          Close
        </Button>
      </div>
    </div>
  );
};
