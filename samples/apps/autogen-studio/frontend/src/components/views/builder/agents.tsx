import {
  ArrowDownTrayIcon,
  ArrowUpTrayIcon,
  DocumentDuplicateIcon,
  InformationCircleIcon,
  PlusIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import { Dropdown, MenuProps, Modal, message } from "antd";
import * as React from "react";
import { IAgent, IStatus } from "../../types";
import { appContext } from "../../../hooks/provider";
import {
  fetchJSON,
  getServerUrl,
  sanitizeConfig,
  timeAgo,
  truncateText,
} from "../../utils";
import { BounceLoader, Card, CardHoverBar, LoadingOverlay } from "../../atoms";
import { AgentViewer } from "./utils/agentconfig";

const AgentsView = ({}: any) => {
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<IStatus | null>({
    status: true,
    message: "All good",
  });

  const { user } = React.useContext(appContext);
  const serverUrl = getServerUrl();
  const listAgentsUrl = `${serverUrl}/agents?user_id=${user?.email}`;

  const [agents, setAgents] = React.useState<IAgent[] | null>([]);
  const [selectedAgent, setSelectedAgent] = React.useState<IAgent | null>(null);

  const [showNewAgentModal, setShowNewAgentModal] = React.useState(false);

  const [showAgentModal, setShowAgentModal] = React.useState(false);

  const sampleAgent = {
    config: {
      name: "sample_agent",
      description: "Sample agent description",
      human_input_mode: "NEVER",
      max_consecutive_auto_reply: 3,
      system_message: "",
    },
  };
  const [newAgent, setNewAgent] = React.useState<IAgent | null>(sampleAgent);

  const deleteAgent = (agent: IAgent) => {
    setError(null);
    setLoading(true);

    const deleteAgentUrl = `${serverUrl}/agents/delete?user_id=${user?.email}&agent_id=${agent.id}`;
    // const fetch;
    const payLoad = {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: user?.email,
        agent: agent,
      }),
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        fetchAgents();
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
    fetchJSON(deleteAgentUrl, payLoad, onSuccess, onError);
  };

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

  React.useEffect(() => {
    if (user) {
      // console.log("fetching messages", messages);
      fetchAgents();
    }
  }, []);

  const agentRows = (agents || []).map((agent: IAgent, i: number) => {
    const cardItems = [
      {
        title: "Download",
        icon: ArrowDownTrayIcon,
        onClick: (e: any) => {
          e.stopPropagation();
          // download workflow as workflow.name.json
          const element = document.createElement("a");
          const sanitizedAgent = sanitizeConfig(agent);
          const file = new Blob([JSON.stringify(sanitizedAgent)], {
            type: "application/json",
          });
          element.href = URL.createObjectURL(file);
          element.download = `agent_${agent.config.name}.json`;
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
          let newAgent = { ...sanitizeConfig(agent) };
          newAgent.config.name = `${agent.config.name}_copy`;
          console.log("newAgent", newAgent);
          setNewAgent(newAgent);
          setShowNewAgentModal(true);
        },
        hoverText: "Make a Copy",
      },
      {
        title: "Delete",
        icon: TrashIcon,
        onClick: (e: any) => {
          e.stopPropagation();
          deleteAgent(agent);
        },
        hoverText: "Delete",
      },
    ];
    return (
      <li
        role="listitem"
        key={"agentrow" + i}
        className=" "
        style={{ width: "200px" }}
      >
        <Card
          className="h-full p-2 cursor-pointer"
          title={
            <div className="  ">
              {truncateText(agent.config.name || "", 25)}
            </div>
          }
          onClick={() => {
            setSelectedAgent(agent);
            setShowAgentModal(true);
          }}
        >
          <div
            style={{ minHeight: "65px" }}
            aria-hidden="true"
            className="my-2   break-words"
          >
            <div className="text-xs mb-2">{agent.type}</div>{" "}
            {truncateText(agent.config.description || "", 70)}
          </div>
          <div
            aria-label={`Updated ${timeAgo(agent.updated_at || "")}`}
            className="text-xs"
          >
            {timeAgo(agent.updated_at || "")}
          </div>
          <CardHoverBar items={cardItems} />
        </Card>
      </li>
    );
  });

  const AgentModal = ({
    agent,
    setAgent,
    showAgentModal,
    setShowAgentModal,
    handler,
  }: {
    agent: IAgent | null;
    setAgent: (agent: IAgent | null) => void;
    showAgentModal: boolean;
    setShowAgentModal: (show: boolean) => void;
    handler?: (agent: IAgent | null) => void;
  }) => {
    const [localAgent, setLocalAgent] = React.useState<IAgent | null>(agent);

    const closeModal = () => {
      setShowAgentModal(false);
      if (handler) {
        handler(localAgent);
      }
    };

    return (
      <Modal
        title={<>Agent Configuration</>}
        width={800}
        open={showAgentModal}
        onOk={() => {
          closeModal();
        }}
        onCancel={() => {
          closeModal();
        }}
        footer={[]}
      >
        {agent && (
          <AgentViewer
            agent={localAgent || agent}
            setAgent={setLocalAgent}
            close={closeModal}
          />
        )}
        {/* {JSON.stringify(localAgent)} */}
      </Modal>
    );
  };

  const uploadAgent = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".json";
    input.onchange = (e: any) => {
      const file = e.target.files[0];
      const reader = new FileReader();
      reader.onload = (e: any) => {
        const contents = e.target.result;
        if (contents) {
          try {
            const agent = JSON.parse(contents);
            // TBD validate that it is a valid agent
            if (!agent.config) {
              throw new Error(
                "Invalid agent file. An agent must have a config"
              );
            }
            setNewAgent(agent);
            setShowNewAgentModal(true);
          } catch (err) {
            message.error(
              "Invalid agent file. Please upload a valid agent file."
            );
          }
        }
      };
      reader.readAsText(file);
    };
    input.click();
  };

  const agentsMenuItems: MenuProps["items"] = [
    // {
    //   type: "divider",
    // },
    {
      key: "uploadagent",
      label: (
        <div>
          <ArrowUpTrayIcon className="w-5 h-5 inline-block mr-2" />
          Upload Agent
        </div>
      ),
    },
  ];

  const agentsMenuItemOnClick: MenuProps["onClick"] = ({ key }) => {
    if (key === "uploadagent") {
      uploadAgent();
      return;
    }
  };

  return (
    <div className="text-primary  ">
      <AgentModal
        agent={selectedAgent}
        setAgent={setSelectedAgent}
        setShowAgentModal={setShowAgentModal}
        showAgentModal={showAgentModal}
        handler={(agent: IAgent | null) => {
          fetchAgents();
        }}
      />

      <AgentModal
        agent={newAgent || sampleAgent}
        setAgent={setNewAgent}
        setShowAgentModal={setShowNewAgentModal}
        showAgentModal={showNewAgentModal}
        handler={(agent: IAgent | null) => {
          fetchAgents();
        }}
      />

      <div className="mb-2   relative">
        <div className="     rounded  ">
          <div className="flex mt-2 pb-2 mb-2 border-b">
            <div className="flex-1 font-semibold mb-2 ">
              {" "}
              Agents ({agentRows.length}){" "}
            </div>
            <div>
              <Dropdown.Button
                type="primary"
                menu={{
                  items: agentsMenuItems,
                  onClick: agentsMenuItemOnClick,
                }}
                placement="bottomRight"
                trigger={["click"]}
                onClick={() => {
                  setShowNewAgentModal(true);
                }}
              >
                <PlusIcon className="w-5 h-5 inline-block mr-1" />
                New Agent
              </Dropdown.Button>
            </div>
          </div>

          <div className="text-xs mb-2 pb-1  ">
            {" "}
            Configure an agent that can reused in your agent workflow .
            <div>
              Tip: You can also create a Group of Agents ( New Agent -
              GroupChat) which can have multiple agents in it.
            </div>
          </div>
          {agents && agents.length > 0 && (
            <div className="w-full  relative">
              <LoadingOverlay loading={loading} />
              <ul className="   flex flex-wrap gap-3">{agentRows}</ul>
            </div>
          )}

          {agents && agents.length === 0 && !loading && (
            <div className="text-sm border mt-4 rounded text-secondary p-2">
              <InformationCircleIcon className="h-4 w-4 inline mr-1" />
              No agents found. Please create a new agent.
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

export default AgentsView;
