import React from "react";
import { Button } from "antd";
import { Plus, GitBranch } from "lucide-react";

interface NewWorkflowControlsProps {
  isLoading: boolean;
  onCreateWorkflow: () => void;
}

const NewWorkflowControls = ({
  isLoading,
  onCreateWorkflow,
}: NewWorkflowControlsProps) => {
  const handleCreateWorkflow = async () => {
    await onCreateWorkflow();
  };

  return (
    <div className="space-y-2 w-full">
      <Button
        type="primary"
        className="w-full"
        onClick={handleCreateWorkflow}
        disabled={isLoading}
        icon={<Plus className="w-4 h-4" />}
      >
        New Workflow
      </Button>

      <div className="text-xs text-secondary flex items-center justify-center gap-1">
        <GitBranch className="w-3 h-3" />
        <span>Graph-based workflow</span>
      </div>
    </div>
  );
};

export default NewWorkflowControls;
