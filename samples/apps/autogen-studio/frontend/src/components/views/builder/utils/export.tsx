import { Button, Modal, message } from "antd";
import * as React from "react";
import { IWorkflow } from "../../../types";
import { ArrowDownTrayIcon } from "@heroicons/react/24/outline";
import {
  checkAndSanitizeInput,
  fetchJSON,
  getServerUrl,
  sanitizeConfig,
} from "../../../utils";
import { appContext } from "../../../../hooks/provider";
import { CodeBlock } from "../../../atoms";

export const ExportWorkflowModal = ({
  workflow,
  show,
  setShow,
}: {
  workflow: IWorkflow | null;
  show: boolean;
  setShow: (show: boolean) => void;
}) => {
  const serverUrl = getServerUrl();
  const { user } = React.useContext(appContext);

  const [error, setError] = React.useState<any>(null);
  const [loading, setLoading] = React.useState<boolean>(false);
  const [workflowDetails, setWorkflowDetails] = React.useState<any>(null);

  const getWorkflowCode = (workflow: IWorkflow) => {
    const workflowCode = `from autogenstudio import WorkflowManager
# load workflow from exported json workflow file.
workflow_manager = WorkflowManager(workflow="path/to/your/workflow_.json")

# run the workflow on a task
task_query = "What is the height of the Eiffel Tower?. Dont write code, just respond to the question."
workflow_manager.run(message=task_query)`;
    return workflowCode;
  };

  const getCliWorkflowCode = (workflow: IWorkflow) => {
    const workflowCode = `autogenstudio serve --workflow=workflow.json --port=5000
    `;
    return workflowCode;
  };

  const getGunicornWorkflowCode = (workflow: IWorkflow) => {
    const workflowCode = `gunicorn -w $((2 * $(getconf _NPROCESSORS_ONLN) + 1)) --timeout 12600 -k uvicorn.workers.UvicornWorker autogenstudio.web.app:app --bind `;

    return workflowCode;
  };

  const fetchWorkFlow = (workflow: IWorkflow) => {
    setError(null);
    setLoading(true);
    // const fetch;
    const payLoad = {
      method: "GET",
      headers: {
        "Content-Type": "application/json",
      },
    };
    const downloadWorkflowUrl = `${serverUrl}/workflows/export/${workflow.id}?user_id=${user?.email}`;

    const onSuccess = (data: any) => {
      if (data && data.status) {
        setWorkflowDetails(data.data);
        console.log("workflow details", data.data);

        const sanitized_name =
          checkAndSanitizeInput(workflow.name).sanitizedText || workflow.name;
        const file_name = `workflow_${sanitized_name}.json`;
        const workflowData = sanitizeConfig(data.data);
        const file = new Blob([JSON.stringify(workflowData)], {
          type: "application/json",
        });
        const downloadUrl = URL.createObjectURL(file);
        const a = document.createElement("a");
        a.href = downloadUrl;
        a.download = file_name;
        a.click();
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
    fetchJSON(downloadWorkflowUrl, payLoad, onSuccess, onError);
  };

  React.useEffect(() => {
    if (workflow && workflow.id && show) {
      // fetchWorkFlow(workflow.id);
      console.log("workflow modal ... component loaded", workflow);
    }
  }, [show]);

  return (
    <Modal
      title={
        <>
          Export Workflow
          <span className="text-accent font-normal ml-2">
            {workflow?.name}
          </span>{" "}
        </>
      }
      width={800}
      open={show}
      onOk={() => {
        setShow(false);
      }}
      onCancel={() => {
        setShow(false);
      }}
      footer={[]}
    >
      <div>
        <div>
          {" "}
          You can use the following steps to start integrating your workflow
          into your application.{" "}
        </div>
        {workflow && workflow.id && (
          <>
            <div className="flex mt-2 gap-3">
              <div>
                <div className="text-sm mt-2 mb-2 pb-1 font-bold">Step 1</div>
                <div className="mt-2 mb-2 pb-1 text-xs">
                  Download your workflow as a JSON file by clicking the button
                  below.
                </div>

                <div className="text-sm mt-2 mb-2 pb-1">
                  <Button
                    type="primary"
                    loading={loading}
                    onClick={() => {
                      fetchWorkFlow(workflow);
                    }}
                  >
                    Download
                    <ArrowDownTrayIcon className="h-4 w-4 inline-block ml-2 -mt-1" />
                  </Button>
                </div>
              </div>

              <div>
                <div className="text-sm mt-2 mb-2 pb-1 font-bold">Step 2</div>
                <div className=" mt-2 mb-2 pb-1 text-xs">
                  Copy the following code snippet and paste it into your
                  application to run your workflow on a task.
                </div>
                <div className="text-sm mt-2 mb-2 pb-1">
                  <CodeBlock
                    className="text-xs"
                    code={getWorkflowCode(workflow)}
                    language="python"
                    wrapLines={true}
                  />
                </div>
              </div>
            </div>

            <div>
              <div className="text-sm mt-2 mb-2 pb-1 font-bold">
                Step 3 (Deploy)
              </div>
              <div className=" mt-2 mb-2 pb-1 text-xs">
                You can also deploy your workflow as an API endpoint using the
                autogenstudio python CLI.
              </div>

              <div className="text-sm mt-2 mb-2 pb-1">
                <CodeBlock
                  className="text-xs"
                  code={getCliWorkflowCode(workflow)}
                  language="bash"
                  wrapLines={true}
                />

                <div className="text-xs mt-2">
                  Note: this will start a endpoint on port 5000. You can change
                  the port by changing the port number. You can also scale this
                  using multiple workers (e.g., via an application server like
                  gunicorn) or wrap it in a docker container and deploy on a
                  cloud provider like Azure.
                </div>

                <CodeBlock
                  className="text-xs"
                  code={getGunicornWorkflowCode(workflow)}
                  language="bash"
                  wrapLines={true}
                />
              </div>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
};
