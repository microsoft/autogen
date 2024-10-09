import React from "react";
import { IWorkflow, IStatus, IChatSession } from "../../../types";
import { ControlRowView } from "../../../atoms";
import {
  fetchJSON,
  getRandomIntFromDateAndSalt,
  getServerUrl,
} from "../../../utils";
import { Button, Drawer, Input, Select, Tabs, message, theme } from "antd";
import { appContext } from "../../../../hooks/provider";
import { BugAntIcon, UserGroupIcon } from "@heroicons/react/24/outline";
import { WorkflowAgentSelector, WorkflowTypeSelector } from "./selectors";
import ChatBox from "../../playground/chatbox";

export const WorkflowViewConfig = ({
  workflow,
  setWorkflow,
  close,
}: {
  workflow: IWorkflow;
  setWorkflow: (newFlowConfig: IWorkflow) => void;
  close: () => void;
}) => {
  const [loading, setLoading] = React.useState<boolean>(false);
  const [error, setError] = React.useState<IStatus | null>(null);
  const { user } = React.useContext(appContext);
  const serverUrl = getServerUrl();
  const createWorkflowUrl = `${serverUrl}/workflows`;

  const [controlChanged, setControlChanged] = React.useState<boolean>(false);
  const [localWorkflow, setLocalWorkflow] = React.useState<IWorkflow>(workflow);

  const updateFlowConfig = (key: string, value: string) => {
    // When an updatedFlowConfig is created using localWorkflow, if the contents of FlowConfigViewer Modal are changed after the Agent Specification Modal is updated, the updated contents of the Agent Specification Modal are not saved. Fixed to localWorkflow->flowConfig. Fixed a bug.
    const updatedFlowConfig = { ...workflow, [key]: value };

    setLocalWorkflow(updatedFlowConfig);
    setWorkflow(updatedFlowConfig);
    setControlChanged(true);
  };

  const createWorkflow = (workflow: IWorkflow) => {
    setError(null);
    setLoading(true);
    // const fetch;
    workflow.user_id = user?.email;

    const payLoad = {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(workflow),
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        const newWorkflow = data.data;
        setWorkflow(newWorkflow);
      } else {
        message.error(data.message);
      }
      setLoading(false);
      // setNewAgent(sampleAgent);
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

    fetchJSON(createWorkflowUrl, payLoad, onSuccess, onError, onFinal);
  };

  const hasChanged = !controlChanged && workflow.id !== undefined;
  const [drawerOpen, setDrawerOpen] = React.useState<boolean>(false);

  const openDrawer = () => {
    setDrawerOpen(true);
  };

  const closeDrawer = () => {
    setDrawerOpen(false);
  };

  const dummySession: IChatSession = {
    user_id: user?.email || "test_session_user_id",
    workflow_id: workflow?.id,
    name: "test_session",
  };

  return (
    <>
      {/* <div className="mb-2">{flowConfig.name}</div> */}
      <div>
        <ControlRowView
          title="Workflow Name"
          className="mt-4 mb-2"
          description="Name of the workflow"
          value={localWorkflow.name}
          control={
            <Input
              className="mt-2 w-full"
              value={localWorkflow.name}
              onChange={(e) => updateFlowConfig("name", e.target.value)}
            />
          }
        />

        <ControlRowView
          title="Workflow Description"
          className="mt-4 mb-2"
          description="Description of the workflow"
          value={localWorkflow.description}
          control={
            <Input
              className="mt-2 w-full"
              value={localWorkflow.description}
              onChange={(e) => updateFlowConfig("description", e.target.value)}
            />
          }
        />

        <ControlRowView
          title="Summary Method"
          description="Defines the method to summarize the conversation"
          value={localWorkflow.summary_method || "last"}
          control={
            <Select
              className="mt-2 w-full"
              defaultValue={localWorkflow.summary_method || "last"}
              onChange={(value: any) =>
                updateFlowConfig("summary_method", value)
              }
              options={
                [
                  { label: "last", value: "last" },
                  { label: "none", value: "none" },
                  { label: "llm", value: "llm" },
                ] as any
              }
            />
          }
        />
      </div>

      <div className="w-full mt-4 text-right">
        {" "}
        {!hasChanged && (
          <Button
            type="primary"
            onClick={() => {
              createWorkflow(localWorkflow);
            }}
            loading={loading}
          >
            {workflow.id ? "Update Workflow" : "Create Workflow"}
          </Button>
        )}
        {workflow?.id && (
          <Button
            className="ml-2 text-primary"
            type="primary"
            onClick={() => {
              setDrawerOpen(true);
            }}
          >
            Test Workflow
          </Button>
        )}
        <Button
          className="ml-2"
          key="close  text-primary"
          type="default"
          onClick={() => {
            close();
          }}
        >
          Close
        </Button>
      </div>

      <Drawer
        title={<div>{workflow?.name || "Test Workflow"}</div>}
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
      </Drawer>
    </>
  );
};

export const WorflowViewer = ({
  workflow,
  setWorkflow,
  close,
}: {
  workflow: IWorkflow;
  setWorkflow: (workflow: IWorkflow) => void;
  close: () => void;
}) => {
  let items = [
    {
      label: (
        <div className="w-full  ">
          {" "}
          <BugAntIcon className="h-4 w-4 inline-block mr-1" />
          Workflow Configuration
        </div>
      ),
      key: "1",
      children: (
        <div>
          {!workflow?.type && (
            <WorkflowTypeSelector
              workflow={workflow}
              setWorkflow={setWorkflow}
            />
          )}

          {workflow?.type && workflow && (
            <WorkflowViewConfig
              workflow={workflow}
              setWorkflow={setWorkflow}
              close={close}
            />
          )}
        </div>
      ),
    },
  ];
  if (workflow) {
    if (workflow?.id) {
      items.push({
        label: (
          <div className="w-full  ">
            {" "}
            <UserGroupIcon className="h-4 w-4 inline-block mr-1" />
            Agents
          </div>
        ),
        key: "2",
        children: (
          <>
            <WorkflowAgentSelector workflow={workflow} />{" "}
          </>
        ),
      });
    }
  }

  const { user } = React.useContext(appContext);

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
