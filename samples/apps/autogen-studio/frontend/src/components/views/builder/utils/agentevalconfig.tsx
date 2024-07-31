import React from "react";
import { IStatus, IAgentEvalCriteria, IModelConfig, IChatSession, IAgentEvalGenerate } from "../../../types";
import { ControlRowView, MonacoEditor } from "../../../atoms";
import {
  fetchJSON,
  getServerUrl,
  truncateText,
} from "../../../utils";
import { Button, Checkbox, Drawer, Input, Modal, Select, Tabs, message, theme } from "antd";
import { appContext } from "../../../../hooks/provider";
import { UserIcon, LightBulbIcon, ArrowDownIcon, ArrowUpIcon } from "@heroicons/react/24/outline";


export const JsonCriteriaViewConfig = ({
  criteria,
  setCriteria,
  models,
  sessions,
  close,
}: {
  criteria: IAgentEvalCriteria;
  setCriteria: (newFlowConfig: IAgentEvalCriteria) => void;
  models: IModelConfig[];
  sessions: IChatSession[];
  close: () => void;
}) => {
  const [loading, setLoading] = React.useState<boolean>(false);
  const [error, setError] = React.useState<IStatus | null>(null);
  const { user } = React.useContext(appContext);
  const serverUrl = getServerUrl();
  const createCriteriaUrl = `${serverUrl}/agenteval/criteria/create`;
  const validateCriteriaUrl = `${serverUrl}/agenteval/criteria/validate`;

  const [controlChanged, setControlChanged] = React.useState<boolean>(false);
  const [localCriteria, setLocalCriteria] = React.useState<IAgentEvalCriteria>(criteria);
  const [validCriteria, setValidCriteria] = React.useState<boolean>(criteria.id);

  const updateFlowConfig = (key: string, value: string) => {
    const updatedFlowConfig = { ...criteria, [key]: value };
    setLocalCriteria(updatedFlowConfig);
    setCriteria(updatedFlowConfig);
    setControlChanged(true);
  };

  const createCriteria = (criteria: IAgentEvalCriteria) => {
    setError(null);
    setLoading(true);
    const payLoad = {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
             "criteria": JSON.parse(criteria.criteria),
             "task": {
                "name": criteria.task_name,
                "description": criteria.task_description,
                "successful_response": "",
                "failed_response": ""
            }
          }),
    };

    const onSuccess = (data: any) => {
      if (data) {
        const newCriteria = data;
        setCriteria(newCriteria);
      } else {
        message.error(data.message);
      }
      setLoading(false);
      close();
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
    fetchJSON(createCriteriaUrl, payLoad, onSuccess, onError, onFinal);
  };

  const validateCriteria = (criteria: IAgentEvalCriteria) => {
    setError(null);
    setLoading(true);

    const payLoad = {
      method: "POST",
      headers: {
        "Content-Type": "text/plain",
      },
      body: criteria.criteria
    };

    const onSuccess = (data: any) => {
      if (data.status) {
        message.success("Criteria successfully validated")
        setValidCriteria(true);
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
    fetchJSON(validateCriteriaUrl, payLoad, onSuccess, onError, onFinal);
  };

  const hasChanged = !controlChanged && criteria.id !== undefined;
  const editorRef = React.useRef<any | null>(null);
  const [showQuantifyModal, setShowQuantifyModal] = React.useState(false);
  const [editorText, setEditorText] = React.useState(!criteria.id ? "Paste your criteria here..." : criteria.criteria);

  return (
    <>
      <div>
        <div>
          <ControlRowView
            title="Task Name"
            className="mt-4 mb-2"
            description="Name of the task that the criteria with evaluate on."
            value = ""
            control={
              <Input
                className="mt-2 w-full"
                value={localCriteria.task_name}
                onChange={(e) => updateFlowConfig("task_name", e.target.value)}
              />
            }
          />
          <ControlRowView
            title="Task Description"
            className="mt-4 mb-2"
            description="Description of the task that the criteria with evaluate on."
            value = ""
            control={
              <Input
                className="mt-2 w-full"
                value={localCriteria.task_description}
                onChange={(e) => updateFlowConfig("task_description", e.target.value)}
              />
            }
          />
        </div>
        <div style={{ height: "45vh" }} className="h-full mb-8 mt-2 rounded">
          {"Criteria"}
          <MonacoEditor
            value={editorText}
            onFocus={() => {
              if (!criteria.criteria) {
                setEditorText('');
              }
            }}
            onBlur={() => {
              if (!criteria.criteria) {
                setEditorText('Paste your criteria here...');
              }
            }}
            language="python"
            editorRef={editorRef}
            onChange={(e) => {
              updateFlowConfig("criteria", e);
              setEditorText(e);
            }}
            style={{ color: !criteria.criteria ? '#BBB' : '#000' }}
          />
        </div>
        <div className="w-full mt-4 text-right">
          {" "}
          <div>
            <Modal
              title={
                <>
                  Quantify Criteria
                  <span className="text-accent font-normal">
                    {localCriteria?.task_name}
                  </span>
                </>
              }
              open={showQuantifyModal}
              onOk={() => setShowQuantifyModal(false)}
              onCancel={() => setShowQuantifyModal(false)}
              footer={[]}
              >
              <QuantifyCriteria
                criteria={criteria}
                serverUrl={serverUrl}
                models={models}
                sessions={sessions}
                user_id={user?.email}
                close={close}
              />
            </Modal>
          </div>
          {!hasChanged && (
            <Button
              className="ml-2"
              type="primary"
              onClick={() => {
                createCriteria(localCriteria);
              }}
              loading={loading}
            >
              {criteria.id ? "Update Criteria" : "Create Criteria"}
            </Button>
          )}
          {criteria.id && validCriteria && (
              <Button
                className="ml-2"
                type="primary"
                onClick={() => setShowQuantifyModal(true)}
                loading={loading}
              >
                Quantify Criteria
              </Button>
            )}
          <Button
            className="ml-2"
            type="primary"
            onClick={() => {
              validateCriteria(localCriteria);
            }}
          >
            Validate Criteria
          </Button>
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
    </>
  );
};


export const CriteriaGenerateConfig = ({
  models,
  sessions,
  close,
}: {
  models: IModelConfig[];
  sessions: IChatSession[];
  close: () => void;
}) => {
  const [loading, setLoading] = React.useState<boolean>(false);
  const [error, setError] = React.useState<IStatus | null>(null);
  const [generateParams, setGenerateParams] = React.useState<IAgentEvalGenerate>({
      user_id: '',
      model_id: 0,
      task_name: '',
      task_description: '',
      success_session_id: 0,
      failure_session_id: 0,
      additional_instructions: '',
      max_round: 5,
      use_subcritic: false
    });
  const [selectedModel, setSelectedModel] = React.useState("");
  const [selectedSuccessSession, setSelectedSuccessSession] = React.useState("");
  const [selectedFailureSession, setSelectedFailureSession] = React.useState("");
  const serverUrl = getServerUrl();
  const generateCriteriaUrl = `${serverUrl}/agenteval/criteria/generate`;

  const generateCriteria = (generateParams: IAgentEvalGenerate) => {
    setError(null);
    setLoading(true);

    const payLoad = {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(generateParams),
    };

    const onSuccess = (data: any) => {
      message.success("New criteria successfully generated.")
      setLoading(false);
      close();
    };
    const onError = (err: any) => {
      setError(err);
      message.error(err.message);
      setLoading(false);
    };
    const onFinal = () => {
      setLoading(false);
    };
    fetchJSON(generateCriteriaUrl, payLoad, onSuccess, onError, onFinal);
  };

  const [isExpanded, setIsExpanded] = React.useState(false);

  return (
    <>
      <div style={{display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between'}}>
        <div style={{flex: 1, marginRight: '20px'}}>
          <ControlRowView
            title="Task Name"
            className="mt-4 mb-2"
            description="Name of the task that the criteria with evaluate on."
            value={""}
            control={
              <Input
                className="mt-2 w-full"
                value={generateParams.task_name}
                onChange={(e) => {
                  setGenerateParams({...generateParams, task_name: e.target.value})
                }}
              />
            }
          />
          <ControlRowView
            title="Task Description"
            className="mt-4 mb-2"
            description="Description of the task that the criteria with evaluate on."
            value={truncateText(generateParams.task_description, 20)}
            control={
              <Input
                className="mt-2 w-full"
                value={generateParams.task_description}
                onChange={(e) => {
                  setGenerateParams({...generateParams, task_description: e.target.value})
                }}
              />
            }
          />
          <ControlRowView
            title="Successful Session Example"
            className="mt-4 mb-2"
            description="Example of a successful agent execution in solving the task."
            value={selectedSuccessSession}
            control={
              <Select
                className="mt-2 w-full"
                onChange={(selectedValue: any) => {
                  setGenerateParams({...generateParams, success_session_id: selectedValue});
                  const selectedSession = sessions.find(session => session.id === selectedValue);
                  setSelectedSuccessSession(selectedSession ? selectedSession.name : "");
                }}
                options={
                  sessions?.map(session => ({
                    value: session.id,
                    label: session.name
                  }))
                }
              />
            }
          />
          <ControlRowView
            title="Failed Session Example"
            className="mt-4 mb-2"
            description="Example of a failed agent execution in solving the task."
            value={selectedFailureSession}
            control={
            <Select
              className="mt-2 w-full"
              onChange={(selectedValue: any) => {
                setGenerateParams({...generateParams, failure_session_id: selectedValue});
                const selectedSession = sessions.find(session => session.id === selectedValue);
                setSelectedFailureSession(selectedSession ? selectedSession.name : "");
              }}
              options={
                sessions?.map(session => ({
                  value: session.id,
                  label: session.name
                }))
              }
            />
            }
          />
        </div>
        <div style={{flex: 1}}>
          <ControlRowView
            title="Model selection"
            className="mt-4 mb-2"
            description="Which model to use during Criteria Generation"
            value={selectedModel}
            control={
            <Select
              className="mt-2 w-full"
              onChange={(selectedValue: any) => {
                console.log("SelectedValue: " + selectedValue)
                setGenerateParams({...generateParams, model_id: selectedValue});
                const selectedModel = models.find(model => model.id === selectedValue);
                setSelectedModel(selectedModel ? selectedModel.model : "");
              }}
              options={
                models?.map(model => ({
                  value: model.id,
                  label: model.model
                }))
              }
            />
            }
          />
          <div>
            <Button
              type="text"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? 'Hide' : 'Show'} Advanced Options
              {isExpanded ? <ArrowUpIcon className="h-4 w-4 inline-block mr-1"/> : <ArrowDownIcon className="h-4 w-4 inline-block mr-1"/>}
            </Button>
            {isExpanded && (
              <>
                <ControlRowView
                  title="Additional Instructions"
                  description="Additional instructions to pass along to the criteria agent."
                  value={truncateText(generateParams.additional_instructions, 20)}
                  control={
                    <Input
                      className="mt-2 w-full"
                      value={generateParams.additional_instructions}
                      onChange={(e) => {
                        setGenerateParams({...generateParams, additional_instructions: e.target.value})
                      }}
                    />
                  }
                />
                <ControlRowView
                  title="Max Rounds"
                  description="The maximum number of rounds of conversation for the CriticAgents to use when coming up with the criteria. (Default: 5)"
                  value={5}
                  control={
                    <Input
                      className="mt-2 w-full"
                      value={generateParams.max_round}
                      onChange={(e) => {
                        setGenerateParams({...generateParams, max_round: e.target.value})
                      }}
                    />
                  }
                />
                <ControlRowView
                  title="Generate subcriteria"
                  description="Check if subcriteria should be generated."
                  value={generateParams.use_subcritic}
                  control={
                    <Checkbox
                      className="mt-2 w-full"
                      onChange={(e) => {
                        setGenerateParams({...generateParams, use_subcritic: e.target.checked})
                      }}
                    />
                  }
                />
              </>
            )}
          </div>
        </div>
      </div>
      <div className="w-full mt-4 text-right">
        {" "}
        <Button
            type="primary"
            onClick={() => {
              generateCriteria(generateParams);
              close();
            }}
            loading={loading}
          >
            Generate Criteria
        </Button>
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
    </>
  );
};

export const CriteriaViewer = ({
  criteria,
  setCriteria,
  models,
  sessions,
  close,
}: {
  criteria: IAgentEvalCriteria;
  setCriteria: (criteria: IAgentEvalCriteria) => void;
  models: IModelConfig[];
  sessions: IChatSession[];
  close: () => void;
}) => {
  let items = [
    {
      label: (
        <div className="w-full  ">
          <UserIcon className="h-4 w-4 inline-block mr-1" />
          User-Defined Criteria
        </div>
      ),
      key: "1",
      children: (
        <div>
          <JsonCriteriaViewConfig
            criteria={criteria}
            setCriteria={setCriteria}
            models={models}
            sessions={sessions}
            close={close}
          />
        </div>
      ),
    },
  ];
  if (!criteria.id) {
    items.push({
      label: (
        <div className="w-full  ">
          <LightBulbIcon className="h-4 w-4 inline-block mr-1" />
          Generate Criteria
        </div>
      ),
      key: "2",
      children: (
        <>
        <div>
          <CriteriaGenerateConfig
            models={models}
            sessions={sessions}
            close={close}
          />
        </div>
        </>
      ),
    });
  }

  return (
    <div className="text-primary">
      <Tabs
        tabBarStyle={{ paddingLeft: 0, marginLeft: 0 }}
        defaultActiveKey="1"
        items={items}
      />
    </div>
  );
};

export const QuantifyCriteria = ({
  criteria,
  serverUrl,
  models,
  sessions,
  user_id,
  close,
}: {
  criteria: IAgentEvalCriteria;
  serverUrl: string;
  models: IModelConfig[];
  sessions: IChatSession[];
  user_id: string;
  close: () => void;
}) => {
  const [loading, setLoading] = React.useState<boolean>(false);
  const [error, setError] = React.useState<IStatus | null>(null);
  const quantifyCriteriaUrl = `${serverUrl}/agenteval/quantify?criteria_id=${criteria.id}&model_id=${criteria.model_id}&test_session_id=${criteria.execution_session_id}&user_id=${user_id}`
  const [selectedSession, setSelectedSession] = React.useState("");
  const [selectedModel, setSelectedModel] = React.useState("");

  const quantifyCriteria = (criteria: IAgentEvalCriteria) => {
    const payLoad = {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        "name": criteria.task_name,
        "description": criteria.task_description,
        "successful_response": "",
        "failed_response": ""
      }),
    };

    const onSuccess = (data: any) => {
      if (data) {
        const element = document.createElement("a");
        const file = new Blob([data], {
          type: "application/json",
        });
        element.href = URL.createObjectURL(file);
        element.download = `results.json`;
        document.body.appendChild(element); // Required for this to work in FireFox
        element.click();
        message.success("Results are in the downloaded file.")
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
    };
    fetchJSON(quantifyCriteriaUrl, payLoad, onSuccess, onError, onFinal);
  };

  return (
    <>
      {/* <div className="mb-2">{flowConfig.name}</div> */}
      <div style={{display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between'}}>
        <div style={{flex: 1, marginRight: '20px'}}>
          <ControlRowView
            title="Test Session"
            className="mt-4 mb-2"
            description="Example of a successful agent execution in solving the task."
            value={selectedSession}
            control={
              <Select
                className="mt-2 w-full"
                onChange={(selectedValue: any) => {
                  const selectedSession = sessions.find(session => session.id === selectedValue);
                  criteria.execution_session_id = selectedSession?.id
                  setSelectedSession(selectedSession ? selectedSession.name : "");
                }}
                options={
                  sessions?.map(session => ({
                    value: session.id,
                    label: session.name
                  }))
                }
              />
            }
          />
          <ControlRowView
            title="Model selection"
            className="mt-4 mb-2"
            description="Which model to use during Criteria Generation"
            value={selectedModel}
            control={
            <Select
              className="mt-2 w-full"
              onChange={(selectedValue: any) => {
                console.log("SelectedValue: " + selectedValue)
                const selectedModel = models.find(model => model.id === selectedValue);
                criteria.model_id = selectedModel?.id
                setSelectedModel(selectedModel ? selectedModel.model : "");
              }}
              options={
                models?.map(model => ({
                  value: model.id,
                  label: model.model
                }))
              }
            />
            }
          />
        </div>
      </div>
      <div>
        {criteria.execution_session_id && criteria.model_id &&
        (<Button
            type="primary"
            onClick={() => {
              quantifyCriteria(criteria);
            }}
            loading={loading}
          >
            Quantify Criteria
        </Button>)}
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
    </>
  );
};
