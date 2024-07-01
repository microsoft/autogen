import React from "react";
import { IStatus, IAgentEvalCriteria, IModelConfig } from "../../../types";
import { ControlRowView, MonacoEditor } from "../../../atoms";
import {
  fetchJSON,
  getRandomIntFromDateAndSalt,
  getServerUrl,
  truncateText,
} from "../../../utils";
import { Button, Checkbox, Drawer, Input, Select, Tabs, message, theme } from "antd";
import { appContext } from "../../../../hooks/provider";
import { UserIcon, LightBulbIcon } from "@heroicons/react/24/outline";
import { WorkflowAgentSelector, WorkflowTypeSelector } from "./selectors";
import ChatBox from "../../playground/chatbox";


export const JsonCriteriaViewConfig = ({
  criteria,
  setCriteria,
  close,
}: {
  criteria: IAgentEvalCriteria;
  setCriteria: (newFlowConfig: IAgentEvalCriteria) => void;
  close: () => void;
}) => {
  const [loading, setLoading] = React.useState<boolean>(false);
  const [error, setError] = React.useState<IStatus | null>(null);
  const serverUrl = getServerUrl();
  const createCriteriaUrl = `${serverUrl}/agenteval/criteria/create?criteria&task`;
  const validateCriteriaUrl = `${serverUrl}/agenteval/criteria/validate/${criteria.criteria}`;

  const [controlChanged, setControlChanged] = React.useState<boolean>(false);
  const [localCriteria, setLocalCriteria] = React.useState<IAgentEvalCriteria>(criteria);

  const updateFlowConfig = (key: string, value: string) => {
    // When an updatedFlowConfig is created using localWorkflow, if the contents of FlowConfigViewer Modal are changed after the Agent Specification Modal is updated, the updated contents of the Agent Specification Modal are not saved. Fixed to localWorkflow->flowConfig. Fixed a bug.
    const updatedFlowConfig = { ...criteria, [key]: value };

    setLocalCriteria(updatedFlowConfig);
    setCriteria(updatedFlowConfig);
    setControlChanged(true);
  };

  const createCriteria = (criteria: IAgentEvalCriteria) => {
    setError(null);
    setLoading(true);
    // const fetch;

    const payLoad = {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: {"criteria": criteria.criteria, 
             "task": {
                "name": criteria.task_name, 
                "description": criteria.task_description, 
                "successful_response": "",
                "failed_response": ""
            }
          },
    };

    const onSuccess = (data: any) => {
      if (data) {
        const newCriteria = data;
        setCriteria(newCriteria);
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
    fetchJSON(createCriteriaUrl, payLoad, onSuccess, onError, onFinal);
  };

  const validateCriteria = (criteria: IAgentEvalCriteria) => {
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
      if (data.status) {
        message.success("Criteria successfully validated")
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

  const quantifyCriteria = (criteria: IAgentEvalCriteria) => {
    setError(null);
    setLoading(true);
    // const fetch;

    const validatePayload = {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    };

    const onValidateSuccess = (data: any) => {
      if (data.status) {
        
      } else {
        message.error(data.message);
      }
      setLoading(false);
    };
    const onValidateError = (err: any) => {
      setError(err);
      message.error(err.message);
      setLoading(false);
    };
    const onValidateFinal = () => {
      setLoading(false);
      setControlChanged(false);
    };
    fetchJSON(validateCriteriaUrl, validatePayload, onValidateSuccess, onValidateError, onValidateFinal);
  }

  const hasChanged = !controlChanged && criteria.id !== undefined;
  const [drawerOpen, setDrawerOpen] = React.useState<boolean>(false);

  const openDrawer = () => {
    setDrawerOpen(true);
  };

  const closeDrawer = () => {
    setDrawerOpen(false);
  };
  const editorRef = React.useRef<any | null>(null);

  return (
    <>
      {/* <div className="mb-2">{flowConfig.name}</div> */}
      <div>
        <ControlRowView
          title="Task Name"
          className="mt-4 mb-2"
          description="Name of the task that the criteria with evaluate on."
          value = ""
          // value={localCriteria.task_name}
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
          // value={localCriteria.task_description}
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
      <div style={{ height: "50vh" }} className="h-full  mt-2 rounded">
        {"Criteria"}
        <MonacoEditor
          value={!criteria.id ? "Paste your criteria here..." : criteria.criteria}
          language="python"
          editorRef={editorRef}
          onChange={(e) => updateFlowConfig("criteria", e)}
        />
      </div>
      <div className="w-full mt-4 text-right">
        <Button
          type="primary"
          onClick={() => {
            quantifyCriteria(localCriteria);
          }}
          loading={loading}
        >
          {"Quantify Criteria"}
        </Button>
        {" "}
        {!hasChanged && (
          <Button
            type="primary"
            onClick={() => {
              createCriteria(localCriteria);
            }}
            loading={loading}
          >
            {criteria.id ? "Update Criteria" : "Create Criteria"}
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

      {/* <Drawer
        title={<div>{criteria?.name || "Test Workflow"}</div>}
        size="large"
        onClose={closeDrawer}
        open={drawerOpen}
      >
        <div className="h-full ">
          {drawerOpen && (
            <ChatBox
              initMessages={[]}
              session={dummySession}
              heightOffset={100}
            />
          )}
        </div>
      </Drawer> */}
    </>
  );
};

export const CriteriaGenerateConfig = ({
  models,
  close,
}: {
  models: IModelConfig[];
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
  const serverUrl = getServerUrl();
  const createCriteriaUrl = `${serverUrl}/agenteval/criteria/create?criteria&task`;
  const generateCriteriaUrl = `${serverUrl}/agenteval/criteria/generate?user_id=guestuser@gmail.com&model_id=${generateParams.model_id}&success_session_id=${generateParams.success_session_id}&failure_session_id=${generateParams.model_id}&additional_instructions=${generateParams.additional_instructions}&max_round=${generateParams.max_round}&use_subcritic=${generateParams.use_subcritic}`;

  const [controlChanged, setControlChanged] = React.useState<boolean>(false);
  

  // const updateFlowConfig = (key: string, value: string) => {
  //   // When an updatedFlowConfig is created using localWorkflow, if the contents of FlowConfigViewer Modal are changed after the Agent Specification Modal is updated, the updated contents of the Agent Specification Modal are not saved. Fixed to localWorkflow->flowConfig. Fixed a bug.
  //   const updatedFlowConfig = { ...params, [key]: value };

  //   setLocalAgentEvalGenerate(updatedFlowConfig);
  //   setControlChanged(true);
  // };

  const generateCriteria = (generateParams: IAgentEvalGenerate) => {
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
              "name": generateParams.task_name, 
              "description": generateParams.task_description, 
              "successful_response": "",
              "failed_response": ""
            }),
    };

    const onSuccess = (data: any) => {
      message.success("New criteria successfully generated.")
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
    console.log(payLoad)
    console.log(payLoad.body)
    fetchJSON(generateCriteriaUrl, payLoad, onSuccess, onError, onFinal);
  };

  const hasChanged = !controlChanged;
  const [drawerOpen, setDrawerOpen] = React.useState<boolean>(false);

  const openDrawer = () => {
    setDrawerOpen(true);
  };

  const closeDrawer = () => {
    setDrawerOpen(false);
  };
  const editorRef = React.useRef<any | null>(null);
  const [isExpanded, setIsExpanded] = React.useState(false);

  return (
    <>
      {/* <div className="mb-2">{flowConfig.name}</div> */}
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
            value={generateParams.success_session_id}
            control={
              <Input
                className="mt-2 w-full"
                value={generateParams.success_session_id}
                onChange={(e) => {
                  setGenerateParams({...generateParams, success_session_id: e.target.value})
                }}
              />
            }
          />
          <ControlRowView
            title="Failed Session Example"
            className="mt-4 mb-2"
            description="Example of a failed agent execution in solving the task."
            value={generateParams.failure_session_id}
            control={
              <Input
                className="mt-2 w-full"
                value={generateParams.failure_session_id}
                onChange={(e) => {
                  setGenerateParams({...generateParams, failure_session_id: e.target.value})
                }}
              />
            }
          />
        </div>
        <div style={{flex: 1}}>
          <ControlRowView
            title="Model selection"
            className="mt-4 mb-2"
            description="Example of a failed agent execution in solving the task."
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
            <button onClick={() => setIsExpanded(!isExpanded)}>
              {isExpanded ? 'Hide' : 'Show'} Advanced Options
            </button>
            {isExpanded && (
              <>
                <ControlRowView
                  title="Additional Instructions"
                  description=""
                  value={""}
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
                  description="The maximum number of rounds of conversation for the Critic agents to use when coming up with the criteria. (Default: 5)"
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
                  title="Use subcritic"
                  description="Checkbox for if the use the SubCritic Agent to create sub criteria."
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
  close,
}: {
  criteria: IAgentEvalCriteria;
  setCriteria: (criteria: IAgentEvalCriteria) => void;
  models: IModelConfig[];
  close: () => void;
}) => {

  

  let items = [
    {
      label: (
        <div className="w-full  ">
          {" "}
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
          {" "}
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
