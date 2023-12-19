import { PlusIcon, TrashIcon } from "@heroicons/react/24/outline";
import { Modal, message } from "antd";
import * as React from "react";
import { IStatus } from "../../types";
import { appContext } from "../../../hooks/provider";
import {
  fetchJSON,
  getSampleSkill,
  getServerUrl,
  truncateText,
} from "../../utils";
import {
  CodeBlock,
  CollapseBox,
  LaunchButton,
  LoadBox,
  LoadingOverlay,
  MarkdownView,
} from "../../atoms";
import { useConfigStore } from "../../../hooks/store";
import TextArea from "antd/es/input/TextArea";

const SkillsView = ({ setMessages, skillup }: any) => {
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<IStatus | null>({
    status: true,
    message: "All good",
  });
  const setSessions = useConfigStore((state) => state.setSessions);

  const { user } = React.useContext(appContext);
  const serverUrl = getServerUrl();
  const clearDbUrl = `${serverUrl}/cleardb`;
  const listSkillsUrl = `${serverUrl}/skills?user_id=${user?.email}`;
  const saveSkillsUrl = `${serverUrl}/skills/`;
  const clearSkillsUrl = `${serverUrl}/skills/clear?user_id=${user?.email}`;

  const [skills, setSkills] = React.useState<any>({});
  const [skillsLoading, setSkillsLoading] = React.useState(false);
  const [selectedSkill, setSelectedSkill] = React.useState<any>(null);

  const [showSkillModal, setShowSkillModal] = React.useState(false);
  const [showNewSkillModal, setShowNewSkillModal] = React.useState(false);

  const sampleSkill = getSampleSkill();
  const [skillCode, setSkillCode] = React.useState(sampleSkill);

  const session = useConfigStore((state) => state.session);

  // console.log("skukkup", skillup);

  const clearDb = () => {
    setError(null);
    setLoading(true);
    // const fetch;
    const payLoad = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: user?.email,
        session: session,
      }),
    };
    console.log("payload", payLoad);
    const onSuccess = (data: any) => {
      console.log(data);
      if (data && data.status) {
        message.success(data.message);
        setMessages([]);
        setSessions(data.data?.sessions);
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
    fetchJSON(clearDbUrl, payLoad, onSuccess, onError);
  };

  React.useEffect(() => {
    if (user) {
      console.log("fetching messages", skillup.get);
      //
      if (skillup.get !== "default") {
        fetchSkills();
      }
    }
  }, [skillup.get]);

  const fetchSkills = () => {
    setError(null);
    setSkillsLoading(true);
    // const fetch;
    const payLoad = {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    };

    const onSuccess = (data: any) => {
      console.log(data);
      if (data && data.status) {
        message.success(data.message);
        console.log("skills", data.data);
        setSkills(data.data);
      } else {
        message.error(data.message);
      }
      setSkillsLoading(false);
    };
    const onError = (err: any) => {
      setError(err);
      message.error(err.message);
      setSkillsLoading(false);
    };
    fetchJSON(listSkillsUrl, payLoad, onSuccess, onError);
  };

  const saveSkill = () => {
    // check if skillTextAreaRef.current is not null or ""

    if (!skillCode || skillCode == "" || skillCode == sampleSkill) {
      message.error("Please provide code for the skill");
      return;
    }

    setError(null);
    setSkillsLoading(true);
    // const fetch;
    const payLoad = {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: user?.email,
        skills: skillCode,
      }),
    };

    const onSuccess = (data: any) => {
      console.log(data);
      if (data && data.status) {
        message.success(data.message);
        console.log("skills", data.data);
        setSkills(data.data);
      } else {
        message.error(data.message);
      }
      setSkillsLoading(false);
      setSkillCode("");
    };
    const onError = (err: any) => {
      setError(err);
      message.error(err.message);
      setSkillsLoading(false);
    };
    fetchJSON(saveSkillsUrl, payLoad, onSuccess, onError);
  };

  React.useEffect(() => {
    if (user) {
      // console.log("fetching messages", messages);
      fetchSkills();
    }
  }, []);

  let userSkills: any[] = [];
  let globalSkills: any[] = [];
  if (skills) {
    userSkills = skills.user;
    globalSkills = skills.global;
  }

  const showSkillRows = (
    skills: any[],
    title: string,
    open: boolean = false
  ) => {
    const skillrows = (skills || []).map((skill: any, i: number) => {
      return (
        <div
          role="button"
          onClick={() => {
            setSelectedSkill(skill);
            setShowSkillModal(true);
          }}
          key={"skillrow" + i}
          className="hover:bg-primary rounded p-2 rounded-b-none duration-300 text-primary text-sm border-b border-dashed py-1 break-all gap-2  "
          title={skill?.docstring}
        >
          {" "}
          <span className="font-semibold">{skill?.name}</span>
          <div className="text-secondary">
            {truncateText(skill.content, 50)}
          </div>
        </div>
      );
    });

    return (
      <div className="mb-2">
        <CollapseBox
          open={open}
          title={
            <div className="font-semibold  ">
              {" "}
              {title} ({skills.length})
            </div>
          }
        >
          <>
            {skillrows}
            {(!skills || skills.length == 0) && (
              <div className="  rounded p-2 px-3 text-xs my-1">
                {" "}
                No {title} created yet.
              </div>
            )}
          </>
        </CollapseBox>
      </div>
    );
  };

  let windowHeight, skillsMaxHeight;
  if (typeof window !== "undefined") {
    windowHeight = window.innerHeight;
    skillsMaxHeight = windowHeight - 400 + "px";
  }

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
        <LoadingOverlay loading={loading} />
        <div
          style={{
            maxHeight: skillsMaxHeight,
          }}
          className="overflow-x-hidden scroll     rounded  "
        >
          <div className="font-semibold mb-2 pb-1 border-b"> Skills </div>
          <div className="text-xs mb-2 pb-1  ">
            {" "}
            Skills are python functions that agents can use to solve tasks.{" "}
          </div>
          {userSkills && <>{showSkillRows(userSkills, "User Skills")}</>}

          {globalSkills && globalSkills.length > 0 && (
            <>{showSkillRows(globalSkills, "Global Skills")}</>
          )}
        </div>

        <div className="flex">
          <div className="flex-1"></div>
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
      </div>

      <hr className="mb-2" />
      <div
        role="button"
        className="inline-block text-xs hover:text-accent"
        onClick={clearDb}
      >
        {!loading && (
          <>
            <TrashIcon className="w-5, h-5 inline-block mr-1" />
            Clear Conversation
          </>
        )}
        {loading && <LoadBox subtitle={"clearing db .."} />}
      </div>
    </div>
  );
};

export default SkillsView;
