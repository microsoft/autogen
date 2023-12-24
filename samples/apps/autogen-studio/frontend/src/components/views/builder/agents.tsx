import {
  InformationCircleIcon,
  PlusIcon,
  TrashIcon,
} from "@heroicons/react/24/outline";
import { Modal, message } from "antd";
import * as React from "react";
import { IAgentFlowSpec, IStatus } from "../../types";
import { appContext } from "../../../hooks/provider";
import { fetchJSON, getServerUrl, timeAgo, truncateText } from "../../utils";
import {
  AgentFlowSpecView,
  Card,
  LaunchButton,
  LoadingOverlay,
} from "../../atoms";

const AgentsView = ({}: any) => {
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<IStatus | null>({
    status: true,
    message: "All good",
  });

  const { user } = React.useContext(appContext);
  const serverUrl = getServerUrl();
  const listAgentsUrl = `${serverUrl}/agents?user_id=${user?.email}`;
  const saveAgentsUrl = `${serverUrl}/agents`;
  const deleteAgentUrl = `${serverUrl}/agents/delete`;

  const [agents, setAgents] = React.useState<IAgentFlowSpec[] | null>([]);
  const [selectedAgent, setSelectedAgent] =
    React.useState<IAgentFlowSpec | null>(null);

  const [showNewAgentModal, setShowNewAgentModal] = React.useState(false);

  const [showAgentModal, setShowAgentModal] = React.useState(false);

  const sampleAgent: IAgentFlowSpec = {
    type: "assistant",
    description: "Sample assistant",
    user_id: user?.email,
    config: {
      name: "sample_assistant",
      llm_config: {
        config_list: [
          {
            model: "gpt-4-1106-preview",
          },
        ],
        temperature: 0.1,
        timeout: 600,
        cache_seed: null,
      },
      human_input_mode: "NEVER",
      max_consecutive_auto_reply: 8,
      system_message: " ..",
    },
  };
  const [newAgent, setNewAgent] = React.useState<IAgentFlowSpec | null>(
    sampleAgent
  );

  const deleteAgent = (agent: IAgentFlowSpec) => {
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
        agent: agent,
      }),
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        console.log("agents", data.data);
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
    fetchJSON(deleteAgentUrl, payLoad, onSuccess, onError);
  };

  const fetchAgent = () => {
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
        console.log("agents", data.data);
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

  const saveAgent = (agent: IAgentFlowSpec) => {
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
        agent: agent,
      }),
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        // console.log("agents", data.data);
        setAgents(data.data);
      } else {
        message.error(data.message);
      }
      setLoading(false);
      setNewAgent(sampleAgent);
    };
    const onError = (err: any) => {
      setError(err);
      message.error(err.message);
      setLoading(false);
    };
    fetchJSON(saveAgentsUrl, payLoad, onSuccess, onError);
  };

  React.useEffect(() => {
    if (user) {
      // console.log("fetching messages", messages);
      fetchAgent();
    }
  }, []);

  React.useEffect(() => {
    if (selectedAgent) {
      console.log("selected agent", selectedAgent);
    }
  }, [selectedAgent]);

  React.useEffect(() => {
    if (newAgent) {
      console.log("new agent", newAgent);
    }
  }, [newAgent]);

  const agentRows = (agents || []).map((agent: IAgentFlowSpec, i: number) => {
    return (
      <div key={"agentrow" + i} className=" " style={{ width: "200px" }}>
        <div className="h-full">
          <Card
            className="h-full p-2 cursor-pointer"
            title={agent.config.name}
            onClick={() => {
              setSelectedAgent(agent);
              setShowAgentModal(true);
            }}
          >
            <div className="my-2">
              {" "}
              {truncateText(agent.description || "", 70)}
            </div>
            <div className="text-xs">{timeAgo(agent.timestamp || "")}</div>
          </Card>
          <div className="text-right mt-2">
            <div
              role="button"
              className="text-accent text-xs inline-block"
              onClick={() => {
                deleteAgent(agent);
              }}
            >
              <TrashIcon className=" w-5, h-5 cursor-pointer inline-block" />
              <span className="text-xs"> delete</span>
            </div>
          </div>
        </div>
      </div>
    );
  });

  const AgentModal = ({
    agent,
    setAgent,
    showAgentModal,
    setShowAgentModal,
    handler,
  }: {
    agent: IAgentFlowSpec | null;
    setAgent: (agent: IAgentFlowSpec | null) => void;
    showAgentModal: boolean;
    setShowAgentModal: (show: boolean) => void;
    handler?: (agent: IAgentFlowSpec | null) => void;
  }) => {
    const [localAgent, setLocalAgent] = React.useState<IAgentFlowSpec | null>(
      agent
    );

    return (
      <Modal
        title={
          <>
            Agent Specification{" "}
            <span className="text-accent font-normal">
              {agent?.config.name}
            </span>{" "}
          </>
        }
        width={800}
        open={showAgentModal}
        onOk={() => {
          setAgent(null);
          setShowAgentModal(false);
          if (handler) {
            handler(localAgent);
          }
        }}
        onCancel={() => {
          setAgent(null);
          setShowAgentModal(false);
        }}
      >
        {agent && (
          <AgentFlowSpecView
            title=""
            flowSpec={localAgent || agent}
            setFlowSpec={setLocalAgent}
          />
        )}
        {/* {JSON.stringify(localAgent)} */}
      </Modal>
    );
  };

  return (
    <div className="  ">
      <AgentModal
        agent={selectedAgent}
        setAgent={setSelectedAgent}
        setShowAgentModal={setShowAgentModal}
        showAgentModal={showAgentModal}
        handler={(agent: IAgentFlowSpec | null) => {
          if (agent) {
            saveAgent(agent);
          }
        }}
      />

      <AgentModal
        agent={newAgent || sampleAgent}
        setAgent={setNewAgent}
        setShowAgentModal={setShowNewAgentModal}
        showAgentModal={showNewAgentModal}
        handler={(agent: IAgentFlowSpec | null) => {
          if (agent) {
            saveAgent(agent);
          }
        }}
      />

      <div className="mb-2   relative">
        <div className="     rounded  ">
          <div className="flex mt-2 pb-2 mb-2 border-b">
            <div className="flex-1 font-semibold mb-2 ">
              {" "}
              Agents ({agentRows.length}){" "}
            </div>
            <LaunchButton
              className="text-sm p-2 px-3"
              onClick={() => {
                setShowNewAgentModal(true);
              }}
            >
              {" "}
              <PlusIcon className="w-5 h-5 inline-block mr-1" />
              New Agent
            </LaunchButton>
          </div>

          <div className="text-xs mb-2 pb-1  ">
            {" "}
            Configure an agent that can reused in your agent workflow{" "}
            {selectedAgent?.config.name}
          </div>
          {agents && agents.length > 0 && (
            <div className="w-full  relative">
              <LoadingOverlay loading={loading} />
              <div className="   flex flex-wrap gap-3">{agentRows}</div>
            </div>
          )}

          {agents && agents.length === 0 && (
            <div className="text-sm border mt-4 rounded text-secondary p-2">
              <InformationCircleIcon className="h-4 w-4 inline mr-1" />
              No agents found. Please create a new agent.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AgentsView;
