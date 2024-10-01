import { Select, message } from "antd";
import * as React from "react";
import { LoadingOverlay } from "../../../atoms";
import { IWorkflow, IStatus } from "../../../types";
import { fetchJSON, getServerUrl } from "../../../utils";
import { appContext } from "../../../../hooks/provider";
import { Link } from "gatsby";

const WorkflowSelector = ({
  workflow,
  setWorkflow,
  workflow_id,
  disabled,
}: {
  workflow: IWorkflow | null;
  setWorkflow: (workflow: IWorkflow) => void;
  workflow_id: number | undefined;
  disabled?: boolean;
}) => {
  const [error, setError] = React.useState<IStatus | null>({
    status: true,
    message: "All good",
  });

  const [loading, setLoading] = React.useState(false);
  const [workflows, setWorkflows] = React.useState<IWorkflow[]>([]);
  const [selectedWorkflow, setSelectedWorkflow] = React.useState<number>(0);

  const { user } = React.useContext(appContext);
  const serverUrl = getServerUrl();
  const listWorkflowsUrl = `${serverUrl}/workflows?user_id=${user?.email}`;
  const fetchWorkFlow = () => {
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
        setWorkflows(data.data);
        if (data.data.length > 0) {
          if (!disabled) {
            setWorkflow(data.data[0]);
          } else {
            const index = data.data.findIndex((item:IWorkflow) => item.id === workflow_id);
            if (index !== -1) {
              setSelectedWorkflow(index);
              setWorkflow(data.data[index]);
            }
          }
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
    fetchJSON(listWorkflowsUrl, payLoad, onSuccess, onError);
  };

  React.useEffect(() => {
    if (user) {
      fetchWorkFlow();
    }
  }, []);

  return (
    <div className=" mb-4 relative">
      <div className="text-sm mt-2 mb-2 pb-1  ">
        {" "}
        Please select an agent workflow to begin.{" "}
      </div>

      <div className="relative mt-2 ">
        <LoadingOverlay loading={loading} />

        {workflows && workflows.length > 0 && (
          <Select
            disabled={disabled}
            className="w-full"
            value={workflows[selectedWorkflow].name}
            onChange={(value: any) => {
              setSelectedWorkflow(value);
              setWorkflow(workflows[value]);
            }}
            options={
              workflows.map((config, index) => {
                return { label: config.name, value: index };
              }) as any
            }
          />
        )}
        <div className="mt-2 text-xs hidden">
          {" "}
          <div className="my-2 text-xs"> {workflow?.name}</div>
          View all workflows{" "}
          <span className="text-accent">
            {" "}
            <Link to="/build">here</Link>
          </span>{" "}
        </div>
      </div>
      {!workflows ||
        (workflows && workflows.length === 0 && (
          <div className="p-1 border rounded text-xs px-2 text-secondary">
            {" "}
            No agent workflows found.
          </div>
        ))}
    </div>
  );
};
export default WorkflowSelector;
