import {
  DocumentTextIcon,
  TrashIcon,
  WrenchIcon,
} from "@heroicons/react/24/outline";
import { Button, Modal, Pagination, Switch, message } from "antd";
import * as React from "react";
import { IStatus } from "../../../types";
import { appContext } from "../../../../hooks/provider";
import { fetchJSON, truncateText } from "../../../utils";
import { CodeBlock } from "../codeblock";
import SkillsView from "./skill";
import ProfileView from "./profile";
import AgentView from "./agent";
import { CollapseBox, LoadBox } from "../../../atoms";

const ClearDBView = ({ setMessages, skillup, config, setMetadata }: any) => {
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<IStatus | null>({
    status: true,
    message: "All good",
  });

  const { user } = React.useContext(appContext);
  const serverUrl = process.env.GATSBY_API_URL;
  const clearDbUrl = `${serverUrl}/cleardb`;
  const listSkillsUrl = `${serverUrl}/skills?user_id=${user?.email}`;
  const clearSkillsUrl = `${serverUrl}/skills/clear?user_id=${user?.email}`;

  const [skills, setSkills] = React.useState<any[]>([]);
  const [skillsLoading, setSkillsLoading] = React.useState(false);

  const [skillsModalOpen, setSkillsModalOpen] = React.useState(false);

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
        userId: user?.email,
      }),
    };
    console.log("payload", payLoad);
    const onSuccess = (data: any) => {
      console.log(data);
      if (data && data.status) {
        message.success(data.message);
        setMessages([]);
        setMetadata({});
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

  const clearSkills = () => {
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
        setSkills(data.skills);
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
    fetchJSON(clearSkillsUrl, payLoad, onSuccess, onError);
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
        setSkills(data.skills);
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

  React.useEffect(() => {
    if (user) {
      // console.log("fetching messages", messages);
      fetchSkills();
    }
  }, []);

  const handleOk = () => {
    setSkillsModalOpen(false);
  };

  const handleCancel = () => {
    setSkillsModalOpen(false);
  };

  let allSkills: any[] = [];
  let userSkills: any[] = [];
  let globalSkills: any[] = [];
  if (skills && skills.length > 0) {
    skills.forEach((skill) => {
      allSkills = allSkills.concat(skill.functions);
      if (skill.file_name.includes("global_utils_dir")) {
        globalSkills = globalSkills.concat(skill.functions);
      } else {
        userSkills = userSkills.concat(skill.functions);
      }
    });
  }

  allSkills = allSkills.reverse();
  userSkills = userSkills.reverse();
  globalSkills = globalSkills.reverse();

  const showSkillRows = (skills: any[]) => {
    return (skills || []).map((skill: any, i: number) => {
      return (
        <div
          key={"skillrow" + i}
          className="text-primary text-sm border-b border-dashed py-1 break-all gap-2  "
          title={skill?.docstring}
        >
          {" "}
          <span className="font-semibold">{skill?.name}</span>
          <div className="text-secondary">
            {truncateText(skill.docstring, 50)}
          </div>
        </div>
      );
    });
  };

  let windowHeight, skillsMaxHeight;
  if (typeof window !== "undefined") {
    windowHeight = window.innerHeight;
    skillsMaxHeight = windowHeight - 400 + "px";
  }

  return (
    <div className="flex flex-col gap-2 flex-wrap">
      <Modal
        title={`(${skills && allSkills.length}) Available Skill${
          skills.length > 1 ? "s" : ""
        }`}
        width={800}
        open={skillsModalOpen}
        onOk={handleOk}
        onCancel={handleCancel}
      >
        {skills && (
          <div>
            <SkillsView skills={skills} />
          </div>
        )}
      </Modal>

      <div className="text-right mt-2">
        <ProfileView config={config} />
      </div>

      <div className="mt-4">
        <div className="hidden text-xs mb-2 break-words">
          There are currently {allSkills.length} skills available. Click below
          to view them.
        </div>

        {allSkills.length > 0 && (
          <div
            style={{
              maxHeight: skillsMaxHeight,
            }}
            className="overflow-x-hidden scroll  mb-4 pr-1   rounded  "
          >
            <div>
              <div className="hidden mb-2  flex">
                <div className="font-semibold flex-1">
                  {" "}
                  User Skills ({userSkills.length})
                </div>
                {userSkills.length > 0 && (
                  <div
                    role="button"
                    onClick={() => {
                      clearSkills();
                    }}
                    className="hover:text-accent duration-300"
                  >
                    <TrashIcon className="w-5 h-5 inline-block" />
                  </div>
                )}
              </div>
              <hr className="mb-2" />

              <CollapseBox
                open={true}
                title={
                  <div className="font-semibold  ">
                    {" "}
                    User Skills ({userSkills.length})
                  </div>
                }
              >
                <>
                  {userSkills.length > 0 && (
                    <div
                      role="button"
                      onClick={() => {
                        clearSkills();
                      }}
                      className="hover:text-accent duration-300 text-right"
                    >
                      {" "}
                      <span className="text-xs mr-1">clear skills</span>
                      <TrashIcon className="w-5 h-5 inline-block" />
                    </div>
                  )}
                  {showSkillRows(userSkills)}
                  {(!userSkills || userSkills.length == 0) && (
                    <div className="bg-secondary rounded p-2 px-3 text-xs my-1">
                      {" "}
                      No user skill created yet.
                    </div>
                  )}
                </>
              </CollapseBox>
            </div>

            <div className="mt-4">
              {/* <hr className="mb-2 mt-2" />
              {showSkillRows(globalSkills)} */}

              <CollapseBox
                open={false}
                title={
                  <div className="font-semibold  ">
                    {" "}
                    Global Skills ({globalSkills.length})
                  </div>
                }
              >
                <>{showSkillRows(globalSkills)}</>
              </CollapseBox>
            </div>
          </div>
        )}

        <Button
          className="block "
          loading={skillsLoading}
          type="default"
          onClick={() => {
            console.log("skills", skills);
            setSkillsModalOpen(true);
          }}
        >
          {!skillsLoading && (
            <WrenchIcon className="w-5, h-5 inline-block mr-1" />
          )}{" "}
          All Skills {skills && `(${allSkills.length})`}
        </Button>
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

      {/* <AgentView config={config} /> */}
    </div>
  );
};

export default ClearDBView;
