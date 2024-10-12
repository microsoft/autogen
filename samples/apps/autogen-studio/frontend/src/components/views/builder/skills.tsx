import {
  ArrowDownTrayIcon,
  ArrowUpTrayIcon,
  CodeBracketIcon,
  CodeBracketSquareIcon,
  DocumentDuplicateIcon,
  InformationCircleIcon,
  KeyIcon,
  PlusIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import { Button, Input, Modal, message, MenuProps, Dropdown, Tabs } from "antd";
import * as React from "react";
import { ISkill, IStatus } from "../../types";
import { appContext } from "../../../hooks/provider";
import {
  fetchJSON,
  getSampleSkill,
  getServerUrl,
  sanitizeConfig,
  timeAgo,
  truncateText,
} from "../../utils";
import {
  BounceLoader,
  Card,
  CardHoverBar,
  LoadingOverlay,
  MonacoEditor,
} from "../../atoms";
import { SkillSelector } from "./utils/selectors";
import { SkillConfigView } from "./utils/skillconfig";

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

  const [skills, setSkills] = React.useState<ISkill[] | null>([]);
  const [selectedSkill, setSelectedSkill] = React.useState<any>(null);

  const [showSkillModal, setShowSkillModal] = React.useState(false);
  const [showNewSkillModal, setShowNewSkillModal] = React.useState(false);

  const sampleSkill = getSampleSkill();
  const [newSkill, setNewSkill] = React.useState<ISkill | null>(sampleSkill);

  const deleteSkill = (skill: ISkill) => {
    setError(null);
    setLoading(true);
    // const fetch;
    const deleteSkillUrl = `${serverUrl}/skills/delete?user_id=${user?.email}&skill_id=${skill.id}`;
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
        fetchSkills();
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
    fetchJSON(deleteSkillUrl, payLoad, onSuccess, onError);
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
        // message.success(data.message);
        console.log("skills", data.data);
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

  React.useEffect(() => {
    if (user) {
      // console.log("fetching messages", messages);
      fetchSkills();
    }
  }, []);

  const skillRows = (skills || []).map((skill: ISkill, i: number) => {
    const cardItems = [
      {
        title: "Download",
        icon: ArrowDownTrayIcon,
        onClick: (e: any) => {
          e.stopPropagation();
          // download workflow as workflow.name.json
          const element = document.createElement("a");
          const sanitizedSkill = sanitizeConfig(skill);
          const file = new Blob([JSON.stringify(sanitizedSkill)], {
            type: "application/json",
          });
          element.href = URL.createObjectURL(file);
          element.download = `skill_${skill.name}.json`;
          document.body.appendChild(element); // Required for this to work in FireFox
          element.click();
        },
        hoverText: "Download",
      },
      {
        title: "Make a Copy",
        icon: DocumentDuplicateIcon,
        onClick: (e: any) => {
          e.stopPropagation();
          let newSkill = { ...sanitizeConfig(skill) };
          newSkill.name = `${skill.name}_copy`;
          setNewSkill(newSkill);
          setShowNewSkillModal(true);
        },
        hoverText: "Make a Copy",
      },
      {
        title: "Delete",
        icon: TrashIcon,
        onClick: (e: any) => {
          e.stopPropagation();
          deleteSkill(skill);
        },
        hoverText: "Delete",
      },
    ];
    return (
      <li key={"skillrow" + i} className=" " style={{ width: "200px" }}>
        <div>
          {" "}
          <Card
            className="h-full p-2 cursor-pointer group"
            title={truncateText(skill.name, 25)}
            onClick={() => {
              setSelectedSkill(skill);
              setShowSkillModal(true);
            }}
          >
            <div
              style={{ minHeight: "65px" }}
              className="my-2   break-words"
              aria-hidden="true"
            >
              {" "}
              {skill.description
                ? truncateText(skill.description || "", 70)
                : truncateText(skill.content || "", 70)}
            </div>
            <div
              aria-label={`Updated ${timeAgo(skill.updated_at || "")}`}
              className="text-xs"
            >
              {timeAgo(skill.updated_at || "")}
            </div>
            <CardHoverBar items={cardItems} />
          </Card>
          <div className="text-right mt-2"></div>
        </div>
      </li>
    );
  });

  const SkillModal = ({
    skill,
    setSkill,
    showSkillModal,
    setShowSkillModal,
    handler,
  }: {
    skill: ISkill | null;
    setSkill: any;
    showSkillModal: boolean;
    setShowSkillModal: any;
    handler: any;
  }) => {
    const editorRef = React.useRef<any | null>(null);
    const [localSkill, setLocalSkill] = React.useState<ISkill | null>(skill);

    const closeModal = () => {
      setSkill(null);
      setShowSkillModal(false);
      if (handler) {
        handler(skill);
      }
    };

    return (
      <Modal
        title={
          <>
            Skill Specification{" "}
            <span className="text-accent font-normal">{localSkill?.name}</span>{" "}
          </>
        }
        width={800}
        open={showSkillModal}
        onCancel={() => {
          setShowSkillModal(false);
        }}
        footer={[]}
      >
        {localSkill && (
          <SkillConfigView
            skill={localSkill}
            setSkill={setLocalSkill}
            close={closeModal}
          />
        )}
      </Modal>
    );
  };

  const uploadSkill = () => {
    const fileInput = document.createElement("input");
    fileInput.type = "file";
    fileInput.accept = ".json";
    fileInput.onchange = (e: any) => {
      const file = e.target.files[0];
      const reader = new FileReader();
      reader.onload = (e) => {
        const content = e.target?.result;
        if (content) {
          try {
            const skill = JSON.parse(content as string);
            if (skill) {
              setNewSkill(skill);
              setShowNewSkillModal(true);
            }
          } catch (e) {
            message.error("Invalid skill file");
          }
        }
      };
      reader.readAsText(file);
    };
    fileInput.click();
  };

  const skillsMenuItems: MenuProps["items"] = [
    // {
    //   type: "divider",
    // },
    {
      key: "uploadskill",
      label: (
        <div>
          <ArrowUpTrayIcon className="w-5 h-5 inline-block mr-2" />
          Upload Skill
        </div>
      ),
    },
  ];

  const skillsMenuItemOnClick: MenuProps["onClick"] = ({ key }) => {
    if (key === "uploadskill") {
      uploadSkill();
      return;
    }
  };

  return (
    <div className=" text-primary ">
      <SkillModal
        skill={selectedSkill}
        setSkill={setSelectedSkill}
        showSkillModal={showSkillModal}
        setShowSkillModal={setShowSkillModal}
        handler={(skill: ISkill) => {
          fetchSkills();
        }}
      />

      <SkillModal
        skill={newSkill || sampleSkill}
        setSkill={setNewSkill}
        showSkillModal={showNewSkillModal}
        setShowSkillModal={setShowNewSkillModal}
        handler={(skill: ISkill) => {
          fetchSkills();
        }}
      />

      <div className="mb-2   relative">
        <div className="">
          <div className="flex mt-2 pb-2 mb-2 border-b">
            <ul className="flex-1   font-semibold mb-2 ">
              {" "}
              Skills ({skillRows.length}){" "}
            </ul>
            <div>
              <Dropdown.Button
                type="primary"
                menu={{
                  items: skillsMenuItems,
                  onClick: skillsMenuItemOnClick,
                }}
                placement="bottomRight"
                trigger={["click"]}
                onClick={() => {
                  setShowNewSkillModal(true);
                }}
              >
                <PlusIcon className="w-5 h-5 inline-block mr-1" />
                New Skill
              </Dropdown.Button>
            </div>
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

          {skills && skills.length === 0 && !loading && (
            <div className="text-sm border mt-4 rounded text-secondary p-2">
              <InformationCircleIcon className="h-4 w-4 inline mr-1" />
              No skills found. Please create a new skill.
            </div>
          )}
          {loading && (
            <div className="  w-full text-center">
              {" "}
              <BounceLoader />{" "}
              <span className="inline-block"> loading .. </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SkillsView;
