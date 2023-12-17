import {
  InformationCircleIcon,
  PlusIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import { Input, Modal, message } from "antd";
import * as React from "react";
import { ISkill, IStatus } from "../../types";
import { appContext } from "../../../hooks/provider";
import {
  fetchJSON,
  getSampleSkill,
  getServerUrl,
  timeAgo,
  truncateText,
} from "../../utils";
import { Card, CodeBlock, LaunchButton, LoadingOverlay } from "../../atoms";
import { useConfigStore } from "../../../hooks/store";
import TextArea from "antd/es/input/TextArea";

const SkillsView = ({}: any) => {
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<IStatus | null>({
    status: true,
    message: "All good",
  });

  const { user } = React.useContext(appContext);
  const serverUrl = getServerUrl();
  const listSkillsUrl = `${serverUrl}/skills?user_id=${user?.email}`;
  const saveSkillsUrl = `${serverUrl}/skills`;
  const deleteSkillsUrl = `${serverUrl}/skills/delete`;

  const [skills, setSkills] = React.useState<ISkill[] | null>([]);
  const [selectedSkill, setSelectedSkill] = React.useState<any>(null);

  const [showSkillModal, setShowSkillModal] = React.useState(false);
  const [showNewSkillModal, setShowNewSkillModal] = React.useState(false);

  const [newSkillTitle, setNewSkillTitle] = React.useState("");

  const sampleSkill = getSampleSkill();
  const [skillCode, setSkillCode] = React.useState(sampleSkill);

  const deleteSkill = (skill: ISkill) => {
    setError(null);
    setLoading(true);
    // const fetch;
    const payLoad = {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: user?.email,
        skill: skill,
      }),
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        setSkills(data.data);
      } else {
        message.error(data.message);
      }
      setLoading(false);
    };
    const onError = (err: any) => {
      setError(err);
      message.error(err.message);
      setLoading(false);
    };
    fetchJSON(deleteSkillsUrl, payLoad, onSuccess, onError);
  };

  const fetchSkills = () => {
    setError(null);
    setLoading(true);
    // const fetch;
    const payLoad = {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        // console.log("skills", data.data);
        setSkills(data.data);
      } else {
        message.error(data.message);
      }
      setLoading(false);
    };
    const onError = (err: any) => {
      setError(err);
      message.error(err.message);
      setLoading(false);
    };
    fetchJSON(listSkillsUrl, payLoad, onSuccess, onError);
  };

  const saveSkill = () => {
    // check if skillTextAreaRef.current is not null or ""

    if (!skillCode || skillCode == "" || skillCode == sampleSkill) {
      message.error("Please provide code for the skill");
      return;
    }

    const skill: ISkill = {
      title: newSkillTitle,
      file_name: "skill.py",
      content: skillCode,
      user_id: user?.email,
    };

    setError(null);
    setLoading(true);
    // const fetch;
    const payLoad = {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: user?.email,
        skill: skill,
      }),
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        // console.log("skills", data.data);
        setSkills(data.data);
      } else {
        message.error(data.message);
      }
      setLoading(false);
      setSkillCode("");
    };
    const onError = (err: any) => {
      setError(err);
      message.error(err.message);
      setLoading(false);
    };
    fetchJSON(saveSkillsUrl, payLoad, onSuccess, onError);
  };

  React.useEffect(() => {
    if (user) {
      // console.log("fetching messages", messages);
      fetchSkills();
    }
  }, []);

  const skillRows = (skills || []).map((skill: ISkill, i: number) => {
    return (
      <div key={"skillrow" + i} className=" " style={{ width: "200px" }}>
        <Card
          className="h-full p-2 cursor-pointer"
          title={skill.title}
          onClick={() => {
            setSelectedSkill(skill);
            setShowSkillModal(true);
          }}
        >
          <div className="my-2"> {truncateText(skill.content, 70)}</div>
          <div className="text-xs">{timeAgo(skill.timestamp || "")}</div>
        </Card>

        <div className="text-right mt-2">
          <div
            role="button"
            className="text-accent text-xs inline-block"
            onClick={() => {
              deleteSkill(skill);
            }}
          >
            <TrashIcon className=" w-5, h-5 cursor-pointer inline-block" />
            <span className="text-xs"> delete</span>
          </div>
        </div>
      </div>
    );
  });

  return (
    <div className="  ">
      <Modal
        title={selectedSkill?.name}
        width={800}
        open={showSkillModal}
        onOk={() => {
          setShowSkillModal(false);
        }}
        onCancel={() => {
          setShowSkillModal(false);
        }}
      >
        {selectedSkill && (
          <div>
            <div className="mb-2">{selectedSkill.file_name}</div>

            <CodeBlock code={selectedSkill?.content} language="python" />
          </div>
        )}
      </Modal>

      <Modal
        title={
          <div>
            <PlusIcon className="w-5 h-5 inline-block mr-1" /> Create New Skill
          </div>
        }
        width={800}
        open={showNewSkillModal}
        onOk={() => {
          saveSkill();
          setShowNewSkillModal(false);
        }}
        onCancel={() => {
          setShowNewSkillModal(false);
        }}
      >
        <>
          <div className="mb-2">
            Provide code for a new skill or create from current conversation.
          </div>
          <Input
            className="mb-2"
            placeholder="Skill Title"
            onChange={(e) => {
              setNewSkillTitle(e.target.value);
            }}
          />
          <TextArea
            value={skillCode}
            onChange={(e) => {
              setSkillCode(e.target.value);
            }}
            rows={10}
          />
        </>
      </Modal>

      <div className="mb-2   relative">
        <div className="">
          <div className="flex mt-2 pb-2 mb-2 border-b">
            <div className="flex-1 font-semibold mb-2 ">
              {" "}
              Skills ({skillRows.length}){" "}
            </div>
            <LaunchButton
              className="text-sm p-2 px-3"
              onClick={() => {
                setShowNewSkillModal(true);
              }}
            >
              {" "}
              <PlusIcon className="w-5 h-5 inline-block mr-1" />
              New Skill
            </LaunchButton>
          </div>
          <div className="text-xs mb-2 pb-1  ">
            {" "}
            Skills are python functions that agents can use to solve tasks.{" "}
          </div>
          {skills && skills.length > 0 && (
            <div
              // style={{ height: "400px" }}
              className="w-full  relative"
            >
              <LoadingOverlay loading={loading} />
              <div className="   flex flex-wrap gap-3">{skillRows}</div>
            </div>
          )}

          {skills && skills.length === 0 && (
            <div className="text-sm border mt-4 rounded text-secondary p-2">
              <InformationCircleIcon className="h-4 w-4 inline mr-1" />
              No skills found. Please create a new skill.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SkillsView;
