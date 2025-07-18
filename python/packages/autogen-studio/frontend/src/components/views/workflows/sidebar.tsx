import React from "react";
import { Button, Tooltip } from "antd";
import {
  Plus,
  Trash2,
  PanelLeftClose,
  PanelLeftOpen,
  GitBranch,
  History,
  InfoIcon,
  RefreshCcw,
} from "lucide-react";
import { Workflow } from "./types";
import { getRelativeTimeString } from "../atoms";
import { getWorkflowTypeColor } from "./utils";
import NewWorkflowControls from "./newworkflow";

interface WorkflowSidebarProps {
  isOpen: boolean;
  workflows: Workflow[];
  currentWorkflow: Workflow | null;
  onToggle: () => void;
  onSelectWorkflow: (workflow: Workflow) => void;
  onCreateWorkflow: () => void;
  onDeleteWorkflow: (workflowId: string) => void;
  isLoading?: boolean;
}

export const WorkflowSidebar: React.FC<WorkflowSidebarProps> = ({
  isOpen,
  workflows,
  currentWorkflow,
  onToggle,
  onSelectWorkflow,
  onCreateWorkflow,
  onDeleteWorkflow,
  isLoading = false,
}) => {
  if (!isOpen) {
    return (
      <div className="h-full border-r border-secondary">
        <div className="p-2 -ml-2">
          <Tooltip
            title={
              <span>
                Workflows{" "}
                <span className="text-accent mx-1"> {workflows.length} </span>
              </span>
            }
          >
            <button
              onClick={onToggle}
              className="p-2 rounded-md hover:bg-secondary hover:text-accent text-secondary transition-colors focus:outline-none focus:ring-2 focus:ring-accent focus:ring-opacity-50"
            >
              <PanelLeftOpen strokeWidth={1.5} className="h-6 w-6" />
            </button>
          </Tooltip>
        </div>
        <div className="mt-4 px-2 -ml-1">
          <Tooltip title="Create new workflow">
            <Button
              type="text"
              className="w-full p-2 flex justify-center"
              onClick={() => onCreateWorkflow()}
              icon={<Plus className="w-4 h-4" />}
            />
          </Tooltip>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full border-r border-secondary">
      <div className="flex items-center justify-between pt-0 p-4 pl-2 pr-2 border-b border-secondary">
        <div className="flex items-center gap-2">
          <span className="text-primary font-medium">Workflows</span>
          <span className="px-2 py-0.5 text-xs bg-accent/10 text-accent rounded">
            {workflows.length}
          </span>
        </div>
        <Tooltip title="Close Sidebar">
          <button
            onClick={onToggle}
            className="p-2 rounded-md hover:bg-secondary hover:text-accent text-secondary transition-colors focus:outline-none focus:ring-2 focus:ring-accent focus:ring-opacity-50"
          >
            <PanelLeftClose strokeWidth={1.5} className="h-6 w-6" />
          </button>
        </Tooltip>
      </div>

      <div className="my-4 flex text-sm">
        <div className="mr-2 w-full pr-2">
          {isOpen && (
            <NewWorkflowControls
              isLoading={isLoading}
              onCreateWorkflow={onCreateWorkflow}
            />
          )}
        </div>
      </div>

      <div className="py-2 flex text-sm text-secondary">
        <History className="w-4 h-4 inline-block mr-1.5" />
        <div className="inline-block -mt-0.5">
          Recents{" "}
          <span className="text-accent text-xs mx-1 mt-0.5">
            {" "}
            ({workflows.length}){" "}
          </span>{" "}
        </div>

        {isLoading && (
          <RefreshCcw className="w-4 h-4 inline-block ml-2 animate-spin" />
        )}
      </div>

      {/* no workflows found */}
      {!isLoading && workflows.length === 0 && (
        <div className="p-2 mr-2 text-center text-secondary text-sm border border-dashed rounded">
          <InfoIcon className="w-4 h-4 inline-block mr-1.5 -mt-0.5" />
          No recent workflows found
        </div>
      )}

      <div className="overflow-y-auto scroll h-[calc(100%-181px)]">
        {workflows.map((workflow) => (
          <div
            key={workflow.id}
            className="relative group"
            onClick={() => onSelectWorkflow(workflow)}
          >
            <div
              className={`
                absolute top-1 left-0.5 z-10 h-[calc(100%-8px)] w-1 rounded
                ${
                  currentWorkflow?.id === workflow.id
                    ? "bg-accent"
                    : "bg-transparent group-hover:bg-secondary"
                }
              `}
            />
            <div
              className={`
                p-2 m-1 ml-2 rounded cursor-pointer transition-colors
                ${
                  currentWorkflow?.id === workflow.id
                    ? "bg-secondary"
                    : "hover:bg-secondary"
                }
              `}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <div
                    className={`p-1.5 rounded ${getWorkflowTypeColor(
                      "workflow"
                    )}`}
                  >
                    <GitBranch className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm truncate text-primary">
                      {workflow.name}
                    </div>
                    <div className="text-xs text-secondary truncate">
                      {getRelativeTimeString(new Date(workflow.updated_at))}
                    </div>
                  </div>
                </div>
                <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                  <Tooltip title="Delete workflow">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDeleteWorkflow(workflow.id);
                      }}
                      className="p-1 rounded hover:bg-red-500/10 text-secondary hover:text-red-500"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </Tooltip>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default WorkflowSidebar;
