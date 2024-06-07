import React from "react";
import { CollapseBox, ControlRowView } from "../../../atoms";
import { checkAndSanitizeInput, fetchJSON, getServerUrl } from "../../../utils";
import {
  Button,
  Form,
  Input,
  Select,
  Slider,
  Tabs,
  message,
  theme,
} from "antd";
import {
  BugAntIcon,
  CpuChipIcon,
  UserGroupIcon,
} from "@heroicons/react/24/outline";
import { appContext } from "../../../../hooks/provider";
import {
  AgentSelector,
  AgentTypeSelector,
  ModelSelector,
  SkillSelector,
} from "./selectors";
import { IAgent, ILLMConfig } from "../../../types";
import TextArea from "antd/es/input/TextArea";

const { useToken } = theme;

export const AgentConfigView = ({
                                  agent,
                                  setAgent,
                                  close,
                                }: {
  agent: IAgent;
  setAgent: (agent: IAgent) => void;
  close: () => void;
}) => {
  const nameValidation = checkAndSanitizeInput(agent?.config?.name);
  const [error, setError] = React.useState<any>(null);
  const [loading, setLoading] = React.useState<boolean>(false);
  const { user } = React.useContext(appContext);
  const serverUrl = getServerUrl();
  const createAgentUrl = `${serverUrl}/agents`;
  const [controlChanged, setControlChanged] = React.useState<boolean>(false);
  const [selectedDbType, setSelectedDbType] = React.useState(agent.config?.retrieve_config?.vector_db);
  const [dbConfig, setDbConfig] = React.useState(agent.config?.retrieve_config?.db_config || {});
  const [selectedAuthType, setSelectedAuthType] = React.useState("String");

  const onControlChange = (value: any, key: string) => {
    const updatedAgent = {
      ...agent,
      config: {
        ...agent.config,
        retrieve_config: {
          ...agent.config.retrieve_config,
          [key]: value,
          db_config: {
            ...agent.config.retrieve_config?.db_config,
            ...dbConfig,
            [key]: value,
          },
        },
      [key]: value,
      },
    };
    if (key === "vector_db") {
      setSelectedDbType(value);
    }
    if (value === "String" || value === "Basic") {
      setSelectedAuthType(value);
    }
    if (["connection_string", "username", "password", "host", "port", "database"].includes(key)) {
      setDbConfig({
        ...dbConfig,
        [key]: value,
      });
    }
    setAgent(updatedAgent);
    setControlChanged(true);
  };

  const llm_config: ILLMConfig = agent?.config?.llm_config || {
    config_list: [],
    temperature: 0.1,
    max_tokens: 4000,
  };

  const createAgent = (agent: IAgent) => {
    setError(null);
    setLoading(true);

    console.log("agent", agent);
    agent.user_id = user?.email;
    const payLoad = {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(agent),
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        console.log("agents", data.data);
        const newAgent = data.data;
        setAgent(newAgent);
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
    const onFinal = () => {
      setLoading(false);
      setControlChanged(false);
    };

    fetchJSON(createAgentUrl, payLoad, onSuccess, onError, onFinal);
  };

  const hasChanged =
      (!controlChanged || !nameValidation.status) && agent?.id !== undefined;

  const validatePort = (value: any) => {
    const port = parseInt(value, 10);
    if (port >= 1 && port <= 65535) {
      onControlChange(port, "port");
    } else {
      // Optionally, you can show a message or handle invalid input differently
      console.warn("Port number must be between 1 and 65535");
    }
  };

  return (
    <div className="text-primary">
      <Form>
        <div
          className={`grid  gap-3 ${
              agent.type === "groupchat" || agent.type === "retrieve_userproxy" ? "grid-cols-2" : "grid-cols-1"
          }`}
        >
          <div className="">
            <ControlRowView
              title="Agent Name"
              className=""
              description="Name of the agent"
              value={agent?.config?.name}
              control={
                <>
                  <Input
                    className="mt-2"
                    placeholder="Agent Name"
                    value={agent?.config?.name}
                    onChange={(e) => {
                      onControlChange(e.target.value, "name");
                    }}
                  />
                  {!nameValidation.status && (
                    <div className="text-xs text-red-500 mt-2">
                      {nameValidation.message}
                    </div>
                  )}
                </>
              }
            />

            <ControlRowView
              title="Agent Description"
              className="mt-4"
              description="Description of the agent, used by other agents (e.g. the GroupChatManager) to decide when to call upon this agent. (Default: system_message)"
              value={agent.config.description || ""}
              control={
                <Input
                  className="mt-2"
                  placeholder="Agent Description"
                  value={agent.config.description || ""}
                  onChange={(e) => {
                    onControlChange(e.target.value, "description");
                  }}
                />
              }
            />

            <ControlRowView
              title="Max Consecutive Auto Reply"
              className="mt-4"
              description="Max consecutive auto reply messages before termination."
              value={agent.config?.max_consecutive_auto_reply}
              control={
                <Slider
                  min={1}
                  max={agent.type === "groupchat" ? 600 : 30}
                  defaultValue={agent.config.max_consecutive_auto_reply}
                  step={1}
                  onChange={(value: any) => {
                    onControlChange(value, "max_consecutive_auto_reply");
                  }}
                />
              }
            />

            <ControlRowView
              title="Human Input Mode"
              description="Defines when to request human input"
              value={agent.config.human_input_mode}
              control={
                <Select
                  className="mt-2 w-full"
                  defaultValue={agent.config.human_input_mode}
                  onChange={(value: any) => {
                    onControlChange(value, "human_input_mode");
                  }}
                  options={
                    [
                      { label: "NEVER", value: "NEVER" },
                    ] as any
                  }
                />
              }
            />

            <ControlRowView
              title="System Message"
              className="mt-4"
              description="Free text to control agent behavior"
              value={agent.config.system_message}
              control={
                <TextArea
                  className="mt-2 w-full"
                  value={agent.config.system_message}
                  rows={3}
                  onChange={(e) => {
                    onControlChange(e.target.value, "system_message");
                  }}
                />
              }
            />

            <div className="mt-4">
              <CollapseBox
                className="bg-secondary mt-4"
                open={false}
                title="Advanced Options"
              >
                <ControlRowView
                  title="Temperature"
                  className="mt-4"
                  description="Defines the randomness of the agent's response."
                  value={llm_config.temperature}
                  control={
                    <Slider
                      min={0}
                      max={2}
                      step={0.1}
                      defaultValue={llm_config.temperature || 0.1}
                      onChange={(value: any) => {
                        const llm_config = {
                          ...agent.config.llm_config,
                          temperature: value,
                        };
                        onControlChange(llm_config, "llm_config");
                      }}
                    />
                  }
                />

                <ControlRowView
                  title="Agent Default Auto Reply"
                  className="mt-4"
                  description="Default auto reply when no code execution or llm-based reply is generated."
                  value={agent.config.default_auto_reply || ""}
                  control={
                    <Input
                      className="mt-2"
                      placeholder="Agent Description"
                      value={agent.config.default_auto_reply || ""}
                      onChange={(e) => {
                        onControlChange(e.target.value, "default_auto_reply");
                      }}
                    />
                  }
                />

                <ControlRowView
                  title="Max Tokens"
                  description="Max tokens generated by LLM used in the agent's response."
                  value={llm_config.max_tokens}
                  className="mt-4"
                  control={
                    <Slider
                      min={100}
                      max={50000}
                      defaultValue={llm_config.max_tokens || 1000}
                      onChange={(value: any) => {
                        const llm_config = {
                          ...agent.config.llm_config,
                          max_tokens: value,
                        };
                        onControlChange(llm_config, "llm_config");
                      }}
                    />
                  }
                />
                <ControlRowView
                  title="Code Execution Config"
                  className="mt-4"
                  description="Determines if and where code execution is done."
                  value={agent.config.code_execution_config || "none"}
                  control={
                    <Select
                      className="mt-2 w-full"
                      defaultValue={agent.config.code_execution_config || "none"}
                      onChange={(value: any) => {
                        onControlChange(value, "code_execution_config");
                      }}
                      options={
                        [
                          { label: "None", value: "none" },
                          { label: "Local", value: "local" },
                          { label: "Docker", value: "docker" },
                        ] as any
                      }
                    />
                  }
                />
              </CollapseBox>
            </div>
          </div>
          {/* ====================== Group Chat Config ======================= */}
          {agent.type === "groupchat" && (
            <div>
              <ControlRowView
                title="Speaker Selection Method"
                description="How the next speaker is selected"
                className=""
                value={agent?.config?.speaker_selection_method || "auto"}
                control={
                  <Select
                    className="mt-2 w-full"
                    defaultValue={
                        agent?.config?.speaker_selection_method || "auto"
                    }
                    onChange={(value: any) => {
                      if (agent?.config) {
                        onControlChange(value, "speaker_selection_method");
                      }
                    }}
                    options={
                      [
                        { label: "Auto", value: "auto" },
                        { label: "Round Robin", value: "round_robin" },
                        { label: "Random", value: "random" },
                      ] as any
                    }
                  />
                }
              />

              <ControlRowView
                title="Admin Name"
                className="mt-4"
                description="Name of the admin of the group chat"
                value={agent.config.admin_name || ""}
                control={
                  <Input
                    className="mt-2"
                    placeholder="Agent Description"
                    value={agent.config.admin_name || ""}
                    onChange={(e) => {
                      onControlChange(e.target.value, "admin_name");
                    }}
                  />
                }
              />

              <ControlRowView
                title="Max Rounds"
                className="mt-4"
                description="Max rounds before termination."
                value={agent.config?.max_round || 10}
                control={
                  <Slider
                    min={10}
                    max={600}
                    defaultValue={agent.config.max_round}
                    step={1}
                    onChange={(value: any) => {
                      onControlChange(value, "max_round");
                    }}
                  />
                }
              />

              <ControlRowView
                title="Allow Repeat Speaker"
                className="mt-4"
                description="Allow the same speaker to speak multiple times in a row"
                value={agent.config?.allow_repeat_speaker || false}
                control={
                  <Select
                    className="mt-2 w-full"
                    defaultValue={agent.config.allow_repeat_speaker}
                    onChange={(value: any) => {
                      onControlChange(value, "allow_repeat_speaker");
                    }}
                    options={
                      [
                        { label: "True", value: true },
                        { label: "False", value: false },
                      ] as any
                    }
                  />
                }
              />
            </div>
          )}
          {/* ====================== Retrieve Chat Config ======================= */}
          {agent.type === "retrieve_userproxy" && (
            <div>
              <ControlRowView
                title="Vector Database"
                className=""
                description="The vector database type. Options include ChromaDB and PGVector. ChromaDB is built into AutoGen Studio. PGVector requires a connection to an external vector database."
                value={agent.config?.retrieve_config?.vector_db || false}
                control={
                  <Select
                    className="mt-2 w-full"
                    defaultValue={agent.config?.retrieve_config?.vector_db}
                    onChange={(value: any) => {
                      onControlChange(value, "vector_db");
                    }}
                    options={
                      [
                        { label: "ChromaDB", value: "ChromaDB" },
                        { label: "PGVector", value: "PGVector" },
                      ] as any
                    }
                  />
                }
              />
              {selectedDbType === "PGVector" && (
                <div>
                  <ControlRowView
                    title="Authentication Type"
                    className=""
                    description="Authentication types include basic auth or connection URI."
                    value={selectedAuthType || ""}
                    control={
                      <Select
                        className="mt-2 w-full"
                        defaultValue="String"
                        onChange={(value: any) => {
                          onControlChange(value, "auth_type");
                        }}
                        options={
                          [
                            { label: "Basic Auth", value: "Basic" },
                            { label: "Connection String", value: "String" },
                          ] as any
                        }
                      />
                    }
                  />
                  {selectedAuthType === "String" && (
                    <div>
                      <ControlRowView
                        title="Connection String"
                        className="mt-4"
                        description="Connection URI postgresql://username:userpass@localhost:5432/database"
                        value={dbConfig.connection_string || ""}
                        control={
                          <Input
                            className="mt-2"
                            placeholder="postgresql://username:userpass@localhost:5432/database"
                            value={dbConfig.connection_string || ""}
                            onChange={(e) => {
                              onControlChange(e.target.value, "connection_string");
                            }}
                          />
                        }
                      />
                    </div>
                  )}

                  {selectedAuthType === "Basic" && (
                    <div>
                      <ControlRowView
                        title="Hostname"
                        className="mt-4"
                        description="PGVector host. This can be an IP address '192.168.1.3' or an FQDN 'dbserver.example'."
                        value={dbConfig.host || ""}
                        control={
                          <Input
                            className="mt-2"
                            placeholder="Hostname"
                            value={dbConfig.host || ""}
                            onChange={(e) => {
                              onControlChange(e.target.value, "host");
                            }}
                          />
                        }
                      />

                      <ControlRowView
                        title="Port"
                        className="mt-4"
                        description="PGVector connection port. This is usually 5432."
                        value={dbConfig.port || ""}
                        control={
                          <Input
                            className="mt-2"
                            placeholder="5432"
                            type="number"
                            min={1}
                            max={65535}
                            value={dbConfig.port || ""}
                            onChange={(e) => {
                              validatePort(e.target.value);
                            }}
                          />
                        }
                      />
                      <ControlRowView
                        title="Database"
                        className="mt-4"
                        description="PGVector database name."
                        value={agent.config?.retrieve_config?.db_config?.database || ""}
                        control={
                          <Input
                            className="mt-2"
                            placeholder="Database"
                            value={agent.config.retrieve_config.db_config.database || ""}
                            onChange={(e) => {
                              onControlChange(e.target.value, "database");
                            }}
                          />
                        }
                      />
                      <ControlRowView
                        title="Username"
                        className="mt-4"
                        description="PGVector database username."
                        value={dbConfig.username || ""}
                        control={
                          <Input
                            className="mt-2"
                            placeholder="Username"
                            value={dbConfig.username || ""}
                            onChange={(e) => {
                              onControlChange(e.target.value, "username");
                            }}
                          />
                        }
                      />

                      <ControlRowView
                        title="Password"
                        className="mt-4"
                        description="PGVector database user password."
                        value="Password"
                        control={
                          <Input
                            type="password"
                            className="mt-2"
                            placeholder=""
                            value={dbConfig.password || ""}
                            onChange={(e) => {
                              onControlChange(e.target.value, "password");
                            }}
                          />
                        }
                      />
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </Form>

      <div className="w-full mt-4 text-right">
        {!hasChanged && (
          <Button
            type="primary"
            onClick={() => {
              createAgent(agent);
              setAgent(agent);
            }}
            loading={loading}
          >
            {agent.id ? "Update Agent" : "Create Agent"}
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

export const AgentViewer = ({
  agent,
  setAgent,
  close,
}: {
  agent: IAgent | null;
  setAgent: (newAgent: IAgent) => void;
  close: () => void;
}) => {
  let items = [
    {
      label: (
        <div className="w-full">
          <BugAntIcon className="h-4 w-4 inline-block mr-1" />
          Agent Configuration
        </div>
      ),
      key: "1",
      children: (
        <div>
          {!agent?.type && (
            <AgentTypeSelector agent={agent} setAgent={setAgent} />
          )}

          {agent?.type && agent && (
            <AgentConfigView agent={agent} setAgent={setAgent} close={close} />
          )}
        </div>
      ),
    },
  ];
  if (agent) {
    if (agent?.id) {
      if (agent.type && agent.type === "groupchat") {
        items.push({
          label: (
            <div className="w-full">
              <UserGroupIcon className="h-4 w-4 inline-block mr-1" />
              Agents
            </div>
          ),
          key: "2",
          children: <AgentSelector agentId={agent?.id} />,
        });
      }

      items.push({
        label: (
          <div className="w-full">
            <CpuChipIcon className="h-4 w-4 inline-block mr-1" />
            Models
          </div>
        ),
        key: "3",
        children: <ModelSelector agentId={agent?.id} />,
      });

      items.push({
        label: (
          <>
            <BugAntIcon className="h-4 w-4 inline-block mr-1" />
            Skills
          </>
        ),
        key: "4",
        children: <SkillSelector agentId={agent?.id} />,
      });
    }
  }

  return (
    <div className="text-primary">
      {/* <RenderView viewIndex={currentViewIndex} /> */}
      <Tabs
        tabBarStyle={{ paddingLeft: 0, marginLeft: 0 }}
        defaultActiveKey="1"
        items={items}
      />
    </div>
  );
};
