import React, { useEffect, useState } from "react";
import { IAgent, IModelConfig, ISkill, IWorkflow } from "../../../types";
import { Card } from "../../../atoms";
import {
  fetchJSON,
  getServerUrl,
  obscureString,
  sampleAgentConfig,
  sampleWorkflowConfig,
  truncateText,
} from "../../../utils";
import {
  Divider,
  Dropdown,
  MenuProps,
  Space,
  Tooltip,
  message,
  theme,
} from "antd";
import {
  CodeBracketSquareIcon,
  ExclamationTriangleIcon,
  InformationCircleIcon,
  PlusIcon,
  RectangleGroupIcon,
  UserCircleIcon,
  XMarkIcon,
} from "@heroicons/react/24/outline";
import { appContext } from "../../../../hooks/provider";

const { useToken } = theme;

export const SkillSelector = ({ agentId }: { agentId: number }) => {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [skills, setSkills] = useState<ISkill[]>([]);
  const [agentSkills, setAgentSkills] = useState<ISkill[]>([]);
  const serverUrl = getServerUrl();
  const { user } = React.useContext(appContext);
  const listSkillsUrl = `${serverUrl}/skills?user_id=${user?.email}`;
  const listAgentSkillsUrl = `${serverUrl}/agents/link/skill/${agentId}`;

  const fetchSkills = () => {
    setError(null);
    setLoading(true);

    const payLoad = {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
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

  const fetchAgentSkills = () => {
    setError(null);
    setLoading(true);

    const payLoad = {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        setAgentSkills(data.data);
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

    fetchJSON(listAgentSkillsUrl, payLoad, onSuccess, onError);
  };

  const linkAgentSkill = (agentId: number, skillId: number) => {
    setError(null);
    setLoading(true);
    const payLoad = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    };
    const linkSkillUrl = `${serverUrl}/agents/link/skill/${agentId}/${skillId}`;
    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        fetchAgentSkills();
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
    fetchJSON(linkSkillUrl, payLoad, onSuccess, onError);
  };

  const unLinkAgentSkill = (agentId: number, skillId: number) => {
    setError(null);
    setLoading(true);
    const payLoad = {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
    };
    const linkSkillUrl = `${serverUrl}/agents/link/skill/${agentId}/${skillId}`;
    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        fetchAgentSkills();
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
    fetchJSON(linkSkillUrl, payLoad, onSuccess, onError);
  };

  useEffect(() => {
    fetchSkills();
    fetchAgentSkills();
  }, [agentId]);

  const skillItems: MenuProps["items"] = skills.map((skill, index) => ({
    key: index,
    label: (
      <>
        <div>{skill.name}</div>
        <div className="text-xs text-accent">
          {truncateText(skill.description || "", 20)}
        </div>
      </>
    ),
    value: index,
  }));

  const skillOnClick: MenuProps["onClick"] = ({ key }) => {
    const selectedIndex = parseInt(key.toString());
    let selectedSkill = skills[selectedIndex];

    if (selectedSkill && selectedSkill.id) {
      linkAgentSkill(agentId, selectedSkill.id);
    }
  };

  const { token } = useToken();
  const contentStyle: React.CSSProperties = {
    backgroundColor: token.colorBgElevated,
    borderRadius: token.borderRadiusLG,
    boxShadow: token.boxShadowSecondary,
  };

  const handleRemoveSkill = (index: number) => {
    const skill = agentSkills[index];
    if (skill && skill.id) {
      unLinkAgentSkill(agentId, skill.id);
    }
  };

  const AddSkillsDropDown = () => {
    return (
      <Dropdown
        menu={{ items: skillItems, onClick: skillOnClick }}
        placement="bottomRight"
        trigger={["click"]}
        dropdownRender={(menu) => (
          <div style={contentStyle}>
            {React.cloneElement(menu as React.ReactElement, {
              style: { boxShadow: "none" },
            })}
            {skills.length === 0 && (
              <>
                <Divider style={{ margin: 0 }} />
                <Space style={{ padding: 8 }}></Space>
                <div className="p-3">
                  {" "}
                  <span className="text-xs">
                    <ExclamationTriangleIcon className="w-4 h-4 inline-block mr-1" />{" "}
                    Please create skills in the Skills tab
                  </span>
                </div>
              </>
            )}
          </div>
        )}
      >
        <div
          className="inline-flex mr-1 mb-1 p-1 px-2 rounded border hover:border-accent duration-300 hover:text-accent"
          role="button"
        >
          add <PlusIcon className="w-4 h-4 inline-block mt-1" />
        </div>
      </Dropdown>
    );
  };

  const agentSkillButtons = agentSkills.map((skill, i) => {
    const tooltipText = (
      <>
        <div>{skill.name}</div>
        <div className="text-xs text-accent">
          {truncateText(skill.description || "", 90)}
        </div>
      </>
    );
    return (
      <div
        key={"skillrow_" + i}
        // role="button"
        className="mr-1 mb-1 p-1 px-2 rounded border"
        // onClick={() => showModal(config, i)}
      >
        <div className="inline-flex">
          {" "}
          <Tooltip title={tooltipText}>
            <div>{skill.name}</div>{" "}
          </Tooltip>
          <div
            role="button"
            onClick={(e) => {
              e.stopPropagation(); // Prevent opening the modal to edit
              handleRemoveSkill(i);
            }}
            className="ml-1 text-primary hover:text-accent duration-300"
          >
            <XMarkIcon className="w-4 h-4 inline-block" />
          </div>
        </div>
      </div>
    );
  });

  return (
    <div>
      {agentSkills && agentSkills.length > 0 && (
        <div className="mb-2">
          <span className="text-accent">{agentSkills.length}</span> Skills
          linked to this agent
        </div>
      )}

      {(!agentSkills || agentSkills.length === 0) && (
        <div className="text-sm border rounded text-secondary p-2 my-2">
          <InformationCircleIcon className="h-4 w-4 inline mr-1" /> No skills
          currently linked to this agent. Please add a skill using the button
          below.
        </div>
      )}

      <div className="flex flex-wrap">
        {agentSkillButtons}
        <AddSkillsDropDown />
      </div>
    </div>
  );
};

export const AgentTypeSelector = ({
  agent,
  setAgent,
}: {
  agent: IAgent | null;
  setAgent: (agent: IAgent) => void;
}) => {
  const iconClass = "h-6 w-6 inline-block ";
  const agentTypes = [
    {
      label: "User Proxy Agent",
      value: "userproxy",
      description: <>Typically represents the user and executes code. </>,
      icon: <UserCircleIcon className={iconClass} />,
    },
    {
      label: "Assistant Agent",
      value: "assistant",
      description: <>Plan and generate code to solve user tasks</>,
      icon: <CodeBracketSquareIcon className={iconClass} />,
    },
    {
      label: "GroupChat ",
      value: "groupchat",
      description: <>Manage group chat interactions</>,
      icon: <RectangleGroupIcon className={iconClass} />,
    },
  ];
  const [selectedAgentType, setSelectedAgentType] = React.useState<
    string | null
  >(null);

  const agentTypeRows = agentTypes.map((agentType: any, i: number) => {
    return (
      <li role="listitem" key={"agenttyperow" + i} className="w-36">
        <Card
          active={selectedAgentType === agentType.value}
          className="h-full p-2 cursor-pointer"
          title={<div className="  ">{agentType.label}</div>}
          onClick={() => {
            setSelectedAgentType(agentType.value);
            if (agent) {
              const sampleAgent = sampleAgentConfig(agentType.value);
              setAgent(sampleAgent);
            }
          }}
        >
          <div style={{ minHeight: "35px" }} className="my-2   break-words ">
            {" "}
            <div className="mb-2">{agentType.icon}</div>
            <span className="text-secondary  tex-sm">
              {" "}
              {agentType.description}
            </span>
          </div>
        </Card>
      </li>
    );
  });

  return (
    <>
      <div className="pb-3">Select Agent Type</div>
      <ul className="inline-flex gap-2">{agentTypeRows}</ul>
    </>
  );
};

export const WorkflowTypeSelector = ({
  workflow,
  setWorkflow,
}: {
  workflow: IWorkflow;
  setWorkflow: (workflow: IWorkflow) => void;
}) => {
  const iconClass = "h-6 w-6 inline-block ";
  const workflowTypes = [
    {
      label: "Default",
      value: "default",
      description: <> Includes a sender and receiver. </>,
      icon: <UserCircleIcon className={iconClass} />,
    },
  ];
  const [seletectedWorkflowType, setSelectedWorkflowType] = React.useState<
    string | null
  >(null);

  const workflowTypeRows = workflowTypes.map((workflowType: any, i: number) => {
    return (
      <li role="listitem" key={"workflowtype" + i} className="w-36">
        <Card
          active={seletectedWorkflowType === workflowType.value}
          className="h-full p-2 cursor-pointer"
          title={<div className="  ">{workflowType.label}</div>}
          onClick={() => {
            setSelectedWorkflowType(workflowType.value);
            if (workflow) {
              const sampleWorkflow = sampleWorkflowConfig();
              setWorkflow(sampleWorkflow);
            }
          }}
        >
          <div style={{ minHeight: "35px" }} className="my-2   break-words">
            {" "}
            <div className="mb-2">{workflowType.icon}</div>
            <span className="text-secondary  tex-sm">
              {" "}
              {workflowType.description}
            </span>
          </div>
        </Card>
      </li>
    );
  });

  return (
    <>
      <div className="pb-3">Select Workflow Type</div>
      <ul className="inline-flex gap-2">{workflowTypeRows}</ul>
    </>
  );
};

export const AgentSelector = ({ agentId }: { agentId: number }) => {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [agents, setAgents] = useState<IAgent[]>([]);
  const [targetAgents, setTargetAgents] = useState<IAgent[]>([]);
  const serverUrl = getServerUrl();
  const { user } = React.useContext(appContext);

  const listAgentsUrl = `${serverUrl}/agents?user_id=${user?.email}`;
  const listTargetAgentsUrl = `${serverUrl}/agents/link/agent/${agentId}`;

  const fetchAgents = () => {
    setError(null);
    setLoading(true);
    const payLoad = {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        setAgents(data.data);
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

    fetchJSON(listAgentsUrl, payLoad, onSuccess, onError);
  };

  const fetchTargetAgents = () => {
    setError(null);
    setLoading(true);
    const payLoad = {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        setTargetAgents(data.data);
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

    fetchJSON(listTargetAgentsUrl, payLoad, onSuccess, onError);
  };

  const linkAgentAgent = (agentId: number, targetAgentId: number) => {
    setError(null);
    setLoading(true);
    const payLoad = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    };
    const linkAgentUrl = `${serverUrl}/agents/link/agent/${agentId}/${targetAgentId}`;
    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        fetchTargetAgents();
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

    fetchJSON(linkAgentUrl, payLoad, onSuccess, onError);
  };

  const unLinkAgentAgent = (agentId: number, targetAgentId: number) => {
    setError(null);
    setLoading(true);
    const payLoad = {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
    };
    const linkAgentUrl = `${serverUrl}/agents/link/agent/${agentId}/${targetAgentId}`;
    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        fetchTargetAgents();
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

    fetchJSON(linkAgentUrl, payLoad, onSuccess, onError);
  };

  useEffect(() => {
    fetchAgents();
    fetchTargetAgents();
  }, []);

  const agentItems: MenuProps["items"] =
    agents.length > 0
      ? agents.map((agent, index) => ({
          key: index,
          label: (
            <>
              <div>{agent.config.name}</div>
              <div className="text-xs text-accent">
                {truncateText(agent.config.description || "", 20)}
              </div>
            </>
          ),
          value: index,
        }))
      : [
          {
            key: -1,
            label: <>No agents found</>,
            value: 0,
          },
        ];

  const agentOnClick: MenuProps["onClick"] = ({ key }) => {
    const selectedIndex = parseInt(key.toString());
    let selectedAgent = agents[selectedIndex];

    if (selectedAgent && selectedAgent.id) {
      linkAgentAgent(agentId, selectedAgent.id);
    }
  };

  const handleRemoveAgent = (index: number) => {
    const agent = targetAgents[index];
    if (agent && agent.id) {
      unLinkAgentAgent(agentId, agent.id);
    }
  };

  const { token } = useToken();
  const contentStyle: React.CSSProperties = {
    backgroundColor: token.colorBgElevated,
    borderRadius: token.borderRadiusLG,
    boxShadow: token.boxShadowSecondary,
  };

  const AddAgentDropDown = () => {
    return (
      <Dropdown
        menu={{ items: agentItems, onClick: agentOnClick }}
        placement="bottomRight"
        trigger={["click"]}
        dropdownRender={(menu) => (
          <div style={contentStyle}>
            {React.cloneElement(menu as React.ReactElement, {
              style: { boxShadow: "none" },
            })}
            {agents.length === 0 && (
              <>
                <Divider style={{ margin: 0 }} />
                <Space style={{ padding: 8 }}></Space>
                <div className="p-3">
                  {" "}
                  <span className="text-xs">
                    <ExclamationTriangleIcon className="w-4 h-4 inline-block mr-1" />{" "}
                    Please create agents in the Agents tab
                  </span>
                </div>
              </>
            )}
          </div>
        )}
      >
        <div
          className="inline-flex mr-1 mb-1 p-1 px-2 rounded border hover:border-accent duration-300 hover:text-accent"
          role="button"
        >
          add <PlusIcon className="w-4 h-4 inline-block mt-1" />
        </div>
      </Dropdown>
    );
  };

  const agentButtons = targetAgents.map((agent, i) => {
    const tooltipText = (
      <>
        <div>{agent.config.name}</div>
        <div className="text-xs text-accent">
          {truncateText(agent.config.description || "", 90)}
        </div>
      </>
    );
    return (
      <div key={"agentrow_" + i} className="mr-1 mb-1 p-1 px-2 rounded border">
        <div className="inline-flex">
          {" "}
          <Tooltip title={tooltipText}>
            <div>{agent.config.name}</div>{" "}
          </Tooltip>
          <div
            role="button"
            onClick={(e) => {
              e.stopPropagation(); // Prevent opening the modal to edit
              handleRemoveAgent(i);
            }}
            className="ml-1 text-primary hover:text-accent duration-300"
          >
            <XMarkIcon className="w-4 h-4 inline-block" />
          </div>
        </div>
      </div>
    );
  });

  return (
    <div>
      {targetAgents && targetAgents.length > 0 && (
        <div className="mb-2">
          <span className="text-accent">{targetAgents.length}</span> Agents
          linked to this agent
        </div>
      )}

      {(!targetAgents || targetAgents.length === 0) && (
        <div className="text-sm border rounded text-secondary p-2 my-2">
          <InformationCircleIcon className="h-4 w-4 inline mr-1" /> No agents
          currently linked to this agent. Please add an agent using the button
          below.
        </div>
      )}

      <div className="flex flex-wrap">
        {agentButtons}
        <AddAgentDropDown />
      </div>
    </div>
  );
};

export const ModelSelector = ({ agentId }: { agentId: number }) => {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [models, setModels] = useState<IModelConfig[]>([]);
  const [agentModels, setAgentModels] = useState<IModelConfig[]>([]);
  const serverUrl = getServerUrl();

  const { user } = React.useContext(appContext);
  const listModelsUrl = `${serverUrl}/models?user_id=${user?.email}`;
  const listAgentModelsUrl = `${serverUrl}/agents/link/model/${agentId}`;

  const fetchModels = () => {
    setError(null);
    setLoading(true);
    const payLoad = {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        // message.success(data.message);
        setModels(data.data);
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
    fetchJSON(listModelsUrl, payLoad, onSuccess, onError);
  };

  const fetchAgentModels = () => {
    setError(null);
    setLoading(true);
    const payLoad = {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        // message.success(data.message);
        setAgentModels(data.data);
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
    fetchJSON(listAgentModelsUrl, payLoad, onSuccess, onError);
  };

  const linkAgentModel = (agentId: number, modelId: number) => {
    setError(null);
    setLoading(true);
    const payLoad = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    };
    const linkModelUrl = `${serverUrl}/agents/link/model/${agentId}/${modelId}`;
    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        console.log("linked model", data);
        fetchAgentModels();
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
    fetchJSON(linkModelUrl, payLoad, onSuccess, onError);
  };

  const unLinkAgentModel = (agentId: number, modelId: number) => {
    setError(null);
    setLoading(true);
    const payLoad = {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
    };
    const linkModelUrl = `${serverUrl}/agents/link/model/${agentId}/${modelId}`;
    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        console.log("unlinked model", data);
        fetchAgentModels();
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
    fetchJSON(linkModelUrl, payLoad, onSuccess, onError);
  };

  useEffect(() => {
    fetchModels();
    fetchAgentModels();
  }, []);

  const modelItems: MenuProps["items"] =
    models.length > 0
      ? models.map((model: IModelConfig, index: number) => ({
          key: index,
          label: (
            <>
              <div>{model.model}</div>
              <div className="text-xs text-accent">
                {truncateText(model.description || "", 20)}
              </div>
            </>
          ),
          value: index,
        }))
      : [
          {
            key: -1,
            label: <>No models found</>,
            value: 0,
          },
        ];

  const modelOnClick: MenuProps["onClick"] = ({ key }) => {
    const selectedIndex = parseInt(key.toString());
    let selectedModel = models[selectedIndex];

    console.log("selected model", selectedModel);
    if (selectedModel && selectedModel.id) {
      linkAgentModel(agentId, selectedModel.id);
    }
  };

  const menuStyle: React.CSSProperties = {
    boxShadow: "none",
  };

  const { token } = useToken();
  const contentStyle: React.CSSProperties = {
    backgroundColor: token.colorBgElevated,
    borderRadius: token.borderRadiusLG,
    boxShadow: token.boxShadowSecondary,
  };

  const AddModelsDropDown = () => {
    return (
      <Dropdown
        menu={{ items: modelItems, onClick: modelOnClick }}
        placement="bottomRight"
        trigger={["click"]}
        dropdownRender={(menu) => (
          <div style={contentStyle}>
            {React.cloneElement(menu as React.ReactElement, {
              style: menuStyle,
            })}
            {models.length === 0 && (
              <>
                <Divider style={{ margin: 0 }} />
                <Space style={{ padding: 8 }}></Space>
                <div className="p-3">
                  <span className="text-xs">
                    {" "}
                    <ExclamationTriangleIcon className="w-4 h-4 inline-block mr-1" />{" "}
                    Please create models in the Model tab
                  </span>
                </div>
              </>
            )}
          </div>
        )}
      >
        <div
          className="inline-flex mr-1 mb-1 p-1 px-2 rounded border hover:border-accent duration-300 hover:text-accent"
          role="button"
        >
          add <PlusIcon className="w-4 h-4 inline-block mt-1" />
        </div>
      </Dropdown>
    );
  };

  const handleRemoveModel = (index: number) => {
    const model = agentModels[index];
    if (model && model.id) {
      unLinkAgentModel(agentId, model.id);
    }
  };

  const agentModelButtons = agentModels.map((model, i) => {
    const tooltipText = (
      <>
        <div>{model.model}</div>
        {model.base_url && <div>{model.base_url}</div>}
        {model.api_key && <div>{obscureString(model.api_key, 3)}</div>}
        <div className="text-xs text-accent">
          {truncateText(model.description || "", 90)}
        </div>
      </>
    );
    return (
      <div
        key={"modelrow_" + i}
        // role="button"
        className="mr-1 mb-1 p-1 px-2 rounded border"
        // onClick={() => showModal(config, i)}
      >
        <div className="inline-flex">
          {" "}
          <Tooltip title={tooltipText}>
            <div>{model.model}</div>{" "}
          </Tooltip>
          <div
            role="button"
            onClick={(e) => {
              e.stopPropagation(); // Prevent opening the modal to edit
              handleRemoveModel(i);
            }}
            className="ml-1 text-primary hover:text-accent duration-300"
          >
            <XMarkIcon className="w-4 h-4 inline-block" />
          </div>
        </div>
      </div>
    );
  });

  return (
    <div className={""}>
      {agentModels && agentModels.length > 0 && (
        <>
          <div className="mb-2">
            {" "}
            <span className="text-accent">{agentModels.length}</span> Models
            linked to this agent{" "}
          </div>
        </>
      )}

      {(!agentModels || agentModels.length == 0) && (
        <div className="text-sm border  rounded text-secondary p-2 my-2">
          <InformationCircleIcon className="h-4 w-4 inline mr-1" />
          No models currently linked to this agent. Please add a model using the
          button below.
        </div>
      )}

      <div className="flex flex-wrap">
        {agentModelButtons}
        <AddModelsDropDown />
      </div>
    </div>
  );
};

export const WorkflowAgentSelector = ({
  workflowId,
}: {
  workflowId: number;
}) => {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [agents, setAgents] = useState<IAgent[]>([]);
  const [senderTargetAgents, setSenderTargetAgents] = useState<IAgent[]>([]);
  const [receiverTargetAgents, setReceiverTargetAgents] = useState<IAgent[]>(
    []
  );
  const serverUrl = getServerUrl();
  const { user } = React.useContext(appContext);

  const listAgentsUrl = `${serverUrl}/agents?user_id=${user?.email}`;

  const fetchAgents = () => {
    setError(null);
    setLoading(true);
    const payLoad = {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        setAgents(data.data);
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

    fetchJSON(listAgentsUrl, payLoad, onSuccess, onError);
  };

  const fetchTargetAgents = (
    setTarget: (arg0: any) => void,
    agentType: string
  ) => {
    const listTargetAgentsUrl = `${serverUrl}/workflows/link/agent/${workflowId}/${agentType}`;
    setError(null);
    setLoading(true);
    const payLoad = {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        setTarget(data.data);
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
    fetchJSON(listTargetAgentsUrl, payLoad, onSuccess, onError);
  };

  const linkWorkflowAgent = (
    workflowId: number,
    targetAgentId: number,
    agentType: string
  ) => {
    setError(null);
    setLoading(true);
    const payLoad = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    };
    const linkAgentUrl = `${serverUrl}/workflows/link/agent/${workflowId}/${targetAgentId}/${agentType}`;
    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        if (agentType === "sender") {
          fetchTargetAgents(setSenderTargetAgents, "sender");
        } else {
          fetchTargetAgents(setReceiverTargetAgents, "receiver");
        }
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

    fetchJSON(linkAgentUrl, payLoad, onSuccess, onError);
  };

  const unlinkWorkflowAgent = (
    workflowId: number,
    targetAgentId: number,
    agentType: string
  ) => {
    setError(null);
    setLoading(true);
    const payLoad = {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
    };
    const unlinkAgentUrl = `${serverUrl}/workflows/link/agent/${workflowId}/${targetAgentId}/${agentType}`;

    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        if (agentType === "sender") {
          fetchTargetAgents(setSenderTargetAgents, "sender");
        } else {
          fetchTargetAgents(setReceiverTargetAgents, "receiver");
        }
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

    fetchJSON(unlinkAgentUrl, payLoad, onSuccess, onError);
  };

  useEffect(() => {
    fetchAgents();
    fetchTargetAgents(setSenderTargetAgents, "sender");
    fetchTargetAgents(setReceiverTargetAgents, "receiver");
  }, []);

  const agentItems: MenuProps["items"] =
    agents.length > 0
      ? agents.map((agent, index) => ({
          key: index,
          label: (
            <>
              <div>{agent.config.name}</div>
              <div className="text-xs text-accent">
                {truncateText(agent.config.description || "", 20)}
              </div>
            </>
          ),
          value: index,
        }))
      : [
          {
            key: -1,
            label: <>No agents found</>,
            value: 0,
          },
        ];

  const receiverOnclick: MenuProps["onClick"] = ({ key }) => {
    const selectedIndex = parseInt(key.toString());
    let selectedAgent = agents[selectedIndex];

    if (selectedAgent && selectedAgent.id) {
      linkWorkflowAgent(workflowId, selectedAgent.id, "receiver");
    }
  };

  const senderOnClick: MenuProps["onClick"] = ({ key }) => {
    const selectedIndex = parseInt(key.toString());
    let selectedAgent = agents[selectedIndex];

    if (selectedAgent && selectedAgent.id) {
      linkWorkflowAgent(workflowId, selectedAgent.id, "sender");
    }
  };

  const handleRemoveAgent = (index: number, agentType: string) => {
    const targetAgents =
      agentType === "sender" ? senderTargetAgents : receiverTargetAgents;
    const agent = targetAgents[index];
    if (agent && agent.id) {
      unlinkWorkflowAgent(workflowId, agent.id, agentType);
    }
  };

  const { token } = useToken();
  const contentStyle: React.CSSProperties = {
    backgroundColor: token.colorBgElevated,
    borderRadius: token.borderRadiusLG,
    boxShadow: token.boxShadowSecondary,
  };

  const AddAgentDropDown = ({
    title,
    onClick,
    agentType,
  }: {
    title?: string;
    onClick: MenuProps["onClick"];
    agentType: string;
  }) => {
    const targetAgents =
      agentType === "sender" ? senderTargetAgents : receiverTargetAgents;
    const agentButtons = targetAgents.map((agent, i) => {
      const tooltipText = (
        <>
          <div>{agent.config.name}</div>
          <div className="text-xs text-accent">
            {truncateText(agent.config.description || "", 90)}
          </div>
        </>
      );
      return (
        <div
          key={"agentrow_" + i}
          className="mr-1 mb-1 p-1 px-2 rounded border"
        >
          <div className="inline-flex">
            {" "}
            <Tooltip title={tooltipText}>
              <div>{agent.config.name}</div>{" "}
            </Tooltip>
            <div
              role="button"
              onClick={(e) => {
                e.stopPropagation(); // Prevent opening the modal to edit
                handleRemoveAgent(i, agentType);
              }}
              className="ml-1 text-primary hover:text-accent duration-300"
            >
              <XMarkIcon className="w-4 h-4 inline-block" />
            </div>
          </div>
        </div>
      );
    });

    return (
      <div>
        <div>
          {(!targetAgents || targetAgents.length === 0) && (
            <div className="text-sm border rounded text-secondary p-2 my-2">
              <InformationCircleIcon className="h-4 w-4 inline mr-1" /> No{" "}
              {title} agent linked to this workflow.
            </div>
          )}
          <div className="flex flex-wrap">{agentButtons} </div>
        </div>

        {targetAgents && targetAgents.length == 1 && (
          <div className="text-xs my-2">
            <InformationCircleIcon className="h-4 w-4 inline mr-1" /> you can
            remove current agents and add new ones.
          </div>
        )}
        {targetAgents && targetAgents.length < 1 && (
          <Dropdown
            menu={{ items: agentItems, onClick: onClick }}
            placement="bottomRight"
            trigger={["click"]}
            dropdownRender={(menu) => (
              <div style={contentStyle}>
                {React.cloneElement(menu as React.ReactElement, {
                  style: { boxShadow: "none" },
                })}
                {agents.length === 0 && (
                  <>
                    <Divider style={{ margin: 0 }} />
                    <Space style={{ padding: 8 }}></Space>
                    <div className="p-3">
                      {" "}
                      <span className="text-xs">
                        <ExclamationTriangleIcon className="w-4 h-4 inline-block mr-1" />{" "}
                        Please create agents in the Agents tab
                      </span>
                    </div>
                  </>
                )}
              </div>
            )}
          >
            <div className="pt-2 border-dashed border-t mt-2">
              {" "}
              <div
                className=" inline-flex mr-1 mb-1 p-1 px-2 rounded border hover:border-accent duration-300 hover:text-accent"
                role="button"
              >
                Add {title} <PlusIcon className="w-4 h-4 inline-block mt-1" />
              </div>
            </div>
          </Dropdown>
        )}
      </div>
    );
  };

  return (
    <div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <h3 className="text-sm mb-2">
            Initiator{" "}
            <Tooltip title={"Agent that initiates the conversation"}>
              <InformationCircleIcon className="h-4 w-4 inline-block" />
            </Tooltip>
          </h3>
          <ul>
            <AddAgentDropDown
              title="Sender"
              onClick={senderOnClick}
              agentType="sender"
            />
          </ul>
        </div>
        <div>
          <h3 className="text-sm mb-2">Receiver</h3>
          <ul>
            <AddAgentDropDown
              title="Receiver"
              onClick={receiverOnclick}
              agentType="receiver"
            />
          </ul>
        </div>
      </div>
    </div>
  );
};
