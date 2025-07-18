import React, { useCallback, useEffect, useState, useContext } from "react";
import { message, Modal } from "antd";
import { ChevronRight } from "lucide-react";
import { appContext } from "../../../hooks/provider";
import { workflowAPI } from "./api";
import { WorkflowSidebar } from "./sidebar";
import { Workflow } from "./types";
import WorkflowBuilder from "./builder";

export const WorkflowManager: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [currentWorkflow, setCurrentWorkflow] = useState<Workflow | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("workflowSidebar");
      return stored !== null ? JSON.parse(stored) : true;
    }
    return true;
  });

  const { user } = useContext(appContext);
  const [messageApi, contextHolder] = message.useMessage();
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // Persist sidebar state
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("workflowSidebar", JSON.stringify(isSidebarOpen));
    }
  }, [isSidebarOpen]);

  const fetchWorkflows = useCallback(async () => {
    try {
      setIsLoading(true);
      const response = await workflowAPI.getWorkflows();
      if (response.success && response.data) {
        setWorkflows(response.data);
        if (!currentWorkflow && response.data.length > 0) {
          setCurrentWorkflow(response.data[0]);
        }
      }
    } catch (error) {
      console.error("Error fetching workflows:", error);
      messageApi.error("Failed to load workflows");
    } finally {
      setIsLoading(false);
    }
  }, [currentWorkflow, messageApi]);

  useEffect(() => {
    fetchWorkflows();
  }, [fetchWorkflows]);

  // Handle URL params
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const workflowId = params.get("workflowId");

    if (workflowId && !currentWorkflow) {
      handleSelectWorkflow({ id: workflowId } as Workflow);
    }
  }, [currentWorkflow]);

  const handleSelectWorkflow = async (selectedWorkflow: Workflow) => {
    if (!selectedWorkflow.id) return;

    if (hasUnsavedChanges) {
      Modal.confirm({
        title: "Unsaved Changes",
        content: "You have unsaved changes. Do you want to discard them?",
        okText: "Discard",
        cancelText: "Go Back",
        onOk: () => {
          switchToWorkflow(selectedWorkflow.id);
        },
      });
    } else {
      await switchToWorkflow(selectedWorkflow.id);
    }
  };

  const switchToWorkflow = async (workflowId: string) => {
    if (!workflowId) return;
    setIsLoading(true);
    try {
      const response = await workflowAPI.getWorkflow(workflowId);
      if (response.success && response.data) {
        setCurrentWorkflow(response.data);
        window.history.pushState({}, "", `?workflowId=${workflowId}`);
        setHasUnsavedChanges(false);
      } else {
        messageApi.error(response.message || "Failed to load workflow");
      }
    } catch (error) {
      console.error("Error loading workflow:", error);
      messageApi.error("Failed to load workflow");
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteWorkflow = async (workflowId: string) => {
    try {
      const response = await workflowAPI.deleteWorkflow(workflowId);
      if (response.success) {
        setWorkflows(workflows.filter((w) => w.id !== workflowId));
        if (currentWorkflow?.id === workflowId) {
          setCurrentWorkflow(
            workflows.find((w) => w.id !== workflowId) || null
          );
        }
        messageApi.success("Workflow deleted");
      } else {
        messageApi.error(response.message || "Failed to delete workflow");
      }
    } catch (error) {
      console.error("Error deleting workflow:", error);
      messageApi.error("Error deleting workflow");
    }
  };

  const handleCreateWorkflow = async () => {
    try {
      const name = "New Workflow";
      const response = await workflowAPI.createWorkflow({
        name,
        description: "A new workflow.",
        config: {
          id: `config-${Date.now()}`,
          name,
          description: "A new workflow.",
          steps: [],
          edges: [],
        },
      });

      if (response.success && response.data) {
        const newWorkflow = response.data;
        setWorkflows([newWorkflow, ...workflows]);
        setCurrentWorkflow(newWorkflow);
        messageApi.success("Workflow created successfully");
      } else {
        messageApi.error(response.message || "Failed to create workflow");
      }
    } catch (error) {
      console.error("Error creating workflow:", error);
      messageApi.error("Error creating workflow");
    }
  };

  const handleWorkflowChange = (workflowData: Partial<Workflow>) => {
    if (!currentWorkflow) return;

    const updatedWorkflow = {
      ...currentWorkflow,
      ...workflowData,
    };

    setCurrentWorkflow(updatedWorkflow);
    setHasUnsavedChanges(true);
  };

  const handleSaveWorkflow = async (workflowData: Partial<Workflow>) => {
    if (!currentWorkflow?.id) return;

    try {
      const response = await workflowAPI.updateWorkflow(currentWorkflow.id, {
        id: currentWorkflow.id,
        name: workflowData.name,
        description: workflowData.description,
        config: workflowData.config,
      });

      if (response.success && response.data) {
        const savedWorkflow = response.data;
        setWorkflows(
          workflows.map((w) => (w.id === savedWorkflow.id ? savedWorkflow : w))
        );
        setCurrentWorkflow(savedWorkflow);
        setHasUnsavedChanges(false);
        messageApi.success("Workflow saved successfully");
      } else {
        messageApi.error(response.message || "Failed to save workflow");
      }
    } catch (error) {
      console.error("Error saving workflow:", error);
      messageApi.error("Error saving workflow");
      throw error;
    }
  };

  return (
    <div className="relative flex h-full w-full">
      {contextHolder}

      {/* Sidebar */}
      <div
        className={`absolute left-0 top-0 h-full transition-all duration-200 ease-in-out z-10 ${
          isSidebarOpen ? "w-64" : "w-12"
        }`}
      >
        <WorkflowSidebar
          isOpen={isSidebarOpen}
          workflows={workflows}
          currentWorkflow={currentWorkflow}
          onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
          onSelectWorkflow={handleSelectWorkflow}
          onCreateWorkflow={handleCreateWorkflow}
          onDeleteWorkflow={handleDeleteWorkflow}
          isLoading={isLoading}
        />
      </div>

      {/* Main Content */}
      <div
        className={`flex-1 transition-all duration-200 ${
          isSidebarOpen ? "ml-64" : "ml-12"
        }`}
      >
        <div className="p-4 pt-2 h-full">
          {/* Breadcrumb */}
          <div className="flex items-center gap-2 mb-4 text-sm">
            <span className="text-primary font-medium">Workflows</span>
            {currentWorkflow && (
              <>
                <ChevronRight className="w-4 h-4 text-secondary" />
                <span className="text-secondary">
                  {currentWorkflow.name}
                  {!currentWorkflow.id && (
                    <span className="text-xs text-orange-500"> (New)</span>
                  )}
                </span>
              </>
            )}
          </div>

          {/* Content Area */}
          {currentWorkflow ? (
            <div className="h-[calc(100vh-120px)]">
              <WorkflowBuilder
                workflow={currentWorkflow}
                onChange={handleWorkflowChange}
                onSave={handleSaveWorkflow}
                onDirtyStateChange={setHasUnsavedChanges}
              />
            </div>
          ) : (
            <div className="flex items-center justify-center h-[calc(100vh-120px)] text-secondary">
              <div className="text-center">
                <h3 className="text-lg font-medium mb-2">Welcome</h3>
                <p className="text-sm mb-4">
                  Select a workflow from the sidebar or create a new one
                </p>
                <div className="flex gap-2 justify-center">
                  <button
                    onClick={() => handleCreateWorkflow()}
                    className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
                  >
                    Create Workflow
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default WorkflowManager;
