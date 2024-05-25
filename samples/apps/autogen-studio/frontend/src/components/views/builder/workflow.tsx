import {
  ArrowDownTrayIcon,
  ArrowUpTrayIcon,
  CodeBracketSquareIcon,
  DocumentDuplicateIcon,
  InformationCircleIcon,
  PlusIcon,
  TrashIcon,
  UserGroupIcon,
  UsersIcon,
} from "@heroicons/react/24/outline";
import { Dropdown, MenuProps, Modal, message } from "antd";
import * as React from "react";
import { IWorkflow, IStatus } from "../../types";
import { appContext } from "../../../hooks/provider";
import {
  fetchJSON,
  getServerUrl,
  sanitizeConfig,
  timeAgo,
  truncateText,
} from "../../utils";
import { BounceLoader, Card, CardHoverBar, LoadingOverlay } from "../../atoms";
import { WorflowViewer } from "./utils/workflowconfig";
import { ExportWorkflowModal } from "./utils/export";

const WorkflowView = ({}: any) => {
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<IStatus | null>({
    status: true,
    message: "All good",
  });
  const { user } = React.useContext(appContext);
  const serverUrl = getServerUrl();
  const listWorkflowsUrl = `${serverUrl}/workflows?user_id=${user?.email}`;
  const saveWorkflowsUrl = `${serverUrl}/workflows`;

  const [workflows, setWorkflows] = React.useState<IWorkflow[] | null>([]);
  const [selectedWorkflow, setSelectedWorkflow] =
    React.useState<IWorkflow | null>(null);
  const [selectedExportWorkflow, setSelectedExportWorkflow] =
    React.useState<IWorkflow | null>(null);

  const sampleWorkflow: IWorkflow = {
    name: "Sample Agent Workflow",
    description: "Sample Agent Workflow",
  };
  const [newWorkflow, setNewWorkflow] = React.useState<IWorkflow | null>(
    sampleWorkflow
  );

  const [showWorkflowModal, setShowWorkflowModal] = React.useState(false);
  const [showNewWorkflowModal, setShowNewWorkflowModal] = React.useState(false);

  const fetchWorkFlow = () => {
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
        setWorkflows(data.data);
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
    fetchJSON(listWorkflowsUrl, payLoad, onSuccess, onError);
  };

  const deleteWorkFlow = (workflow: IWorkflow) => {
    setError(null);
    setLoading(true);
    // const fetch;
    const deleteWorkflowsUrl = `${serverUrl}/workflows/delete?user_id=${user?.email}&workflow_id=${workflow.id}`;
    const payLoad = {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: user?.email,
        workflow: workflow,
      }),
    };

    const onSuccess = (data: any) => {
      if (data && data.status) {
        message.success(data.message);
        fetchWorkFlow();
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
    fetchJSON(deleteWorkflowsUrl, payLoad, onSuccess, onError);
  };

  React.useEffect(() => {
    if (user) {
      // console.log("fetching messages", messages);
      fetchWorkFlow();
    }
  }, []);

  React.useEffect(() => {
    if (selectedWorkflow) {
      setShowWorkflowModal(true);
    }
  }, [selectedWorkflow]);

  const [showExportModal, setShowExportModal] = React.useState(false);

  const workflowRows = (workflows || []).map(
    (workflow: IWorkflow, i: number) => {
      const cardItems = [
        {
          title: "Export",
          icon: CodeBracketSquareIcon,
          onClick: (e: any) => {
            e.stopPropagation();
            setSelectedExportWorkflow(workflow);
            setShowExportModal(true);
          },
          hoverText: "Export",
        },
        {
          title: "Download",
          icon: ArrowDownTrayIcon,
          onClick: (e: any) => {
            e.stopPropagation();
            // download workflow as workflow.name.json
            const element = document.createElement("a");
            const sanitizedWorkflow = sanitizeConfig(workflow);
            const file = new Blob([JSON.stringify(sanitizedWorkflow)], {
              type: "application/json",
            });
            element.href = URL.createObjectURL(file);
            element.download = `workflow_${workflow.name}.json`;
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
            let newWorkflow = { ...sanitizeConfig(workflow) };
            newWorkflow.name = `${workflow.name}_copy`;
            setNewWorkflow(newWorkflow);
            setShowNewWorkflowModal(true);
          },
          hoverText: "Make a Copy",
        },
        {
          title: "Delete",
          icon: TrashIcon,
          onClick: (e: any) => {
            e.stopPropagation();
            deleteWorkFlow(workflow);
          },
          hoverText: "Delete",
        },
      ];
      return (
        <li
          key={"workflowrow" + i}
          className="block   h-full"
          style={{ width: "200px" }}
        >
          <Card
            className="  block p-2 cursor-pointer"
            title={<div className="  ">{truncateText(workflow.name, 25)}</div>}
            onClick={() => {
              setSelectedWorkflow(workflow);
            }}
          >
            <div
              style={{ minHeight: "65px" }}
              className="break-words  my-2"
              aria-hidden="true"
            >
              <div className="text-xs mb-2">{workflow.type}</div>{" "}
              {truncateText(workflow.description, 70)}
            </div>
            <div
              aria-label={`Updated ${timeAgo(workflow.updated_at || "")} ago`}
              className="text-xs"
            >
              {timeAgo(workflow.updated_at || "")}
            </div>

            <CardHoverBar items={cardItems} />
          </Card>
        </li>
      );
    }
  );

  const WorkflowModal = ({
    workflow,
    setWorkflow,
    showModal,
    setShowModal,
    handler,
  }: {
    workflow: IWorkflow | null;
    setWorkflow?: (workflow: IWorkflow | null) => void;
    showModal: boolean;
    setShowModal: (show: boolean) => void;
    handler?: (workflow: IWorkflow) => void;
  }) => {
    const [localWorkflow, setLocalWorkflow] = React.useState<IWorkflow | null>(
      workflow
    );

    const closeModal = () => {
      setShowModal(false);
      if (handler) {
        handler(localWorkflow as IWorkflow);
      }
    };

    return (
      <Modal
        title={
          <>
            Workflow Specification{" "}
            <span className="text-accent font-normal">
              {localWorkflow?.name}
            </span>{" "}
          </>
        }
        width={800}
        open={showModal}
        onOk={() => {
          closeModal();
        }}
        onCancel={() => {
          closeModal();
        }}
        footer={[]}
      >
        <>
          {localWorkflow && (
            <WorflowViewer
              workflow={localWorkflow}
              setWorkflow={setLocalWorkflow}
              close={closeModal}
            />
          )}
        </>
      </Modal>
    );
  };

  const uploadWorkflow = () => {
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
            const workflow = JSON.parse(contents);
            // TBD validate that it is a valid workflow
            setNewWorkflow(workflow);
            setShowNewWorkflowModal(true);
          } catch (err) {
            message.error("Invalid workflow file");
          }
        }
      };
      reader.readAsText(file);
    };
    input.click();
  };

  const workflowTypes: MenuProps["items"] = [
    // {
    //   key: "twoagents",
    //   label: (
    //     <div>
    //       {" "}
    //       <UsersIcon className="w-5 h-5 inline-block mr-2" />
    //       Two Agents
    //     </div>
    //   ),
    // },
    // {
    //   key: "groupchat",
    //   label: (
    //     <div>
    //       <UserGroupIcon className="w-5 h-5 inline-block mr-2" />
    //       Group Chat
    //     </div>
    //   ),
    // },
    // {
    //   type: "divider",
    // },
    {
      key: "uploadworkflow",
      label: (
        <div>
          <ArrowUpTrayIcon className="w-5 h-5 inline-block mr-2" />
          Upload Workflow
        </div>
      ),
    },
  ];

  const showWorkflow = (config: IWorkflow) => {
    setSelectedWorkflow(config);
    setShowWorkflowModal(true);
  };

  const workflowTypesOnClick: MenuProps["onClick"] = ({ key }) => {
    if (key === "uploadworkflow") {
      uploadWorkflow();
      return;
    }
    showWorkflow(sampleWorkflow);
  };

  return (
    <div className=" text-primary ">
      <WorkflowModal
        workflow={selectedWorkflow}
        setWorkflow={setSelectedWorkflow}
        showModal={showWorkflowModal}
        setShowModal={setShowWorkflowModal}
        handler={(workflow: IWorkflow) => {
          fetchWorkFlow();
        }}
      />

      <WorkflowModal
        workflow={newWorkflow}
        showModal={showNewWorkflowModal}
        setShowModal={setShowNewWorkflowModal}
        handler={(workflow: IWorkflow) => {
          fetchWorkFlow();
        }}
      />

      <ExportWorkflowModal
        workflow={selectedExportWorkflow}
        show={showExportModal}
        setShow={setShowExportModal}
      />

      <div className="mb-2   relative">
        <div className="     rounded  ">
          <div className="flex mt-2 pb-2 mb-2 border-b">
            <div className="flex-1 font-semibold  mb-2 ">
              {" "}
              Workflows ({workflowRows.length}){" "}
            </div>
            <div className=" ">
              <Dropdown.Button
                type="primary"
                menu={{ items: workflowTypes, onClick: workflowTypesOnClick }}
                placement="bottomRight"
                trigger={["click"]}
                onClick={() => {
                  showWorkflow(sampleWorkflow);
                }}
              >
                <PlusIcon className="w-5 h-5 inline-block mr-1" />
                New Workflow
              </Dropdown.Button>
            </div>
          </div>
          <div className="text-xs mb-2 pb-1  ">
            {" "}
            Configure an agent workflow that can be used to handle tasks.
          </div>
          {workflows && workflows.length > 0 && (
            <div
              // style={{ minHeight: "500px" }}
              className="w-full relative"
            >
              <LoadingOverlay loading={loading} />
              <ul className="flex flex-wrap gap-3">{workflowRows}</ul>
            </div>
          )}
          {workflows && workflows.length === 0 && !loading && (
            <div className="text-sm border mt-4 rounded text-secondary p-2">
              <InformationCircleIcon className="h-4 w-4 inline mr-1" />
              No workflows found. Please create a new workflow.
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

export default WorkflowView;
