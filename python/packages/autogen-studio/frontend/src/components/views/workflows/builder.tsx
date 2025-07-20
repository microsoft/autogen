import React, {
  useCallback,
  useEffect,
  useState,
  useContext,
  useRef,
} from "react";
import {
  ReactFlow,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Background,
  MiniMap,
  Panel,
  Node,
  Edge,
  BackgroundVariant,
  NodeProps,
  NodeTypes,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { message, Drawer, Button, Switch } from "antd";
import {
  Play,
  CheckCircle,
  XCircle,
  Clock,
  Loader2,
  AlertCircle,
  Code2,
  Cable,
} from "lucide-react";
import {
  Workflow,
  StepConfig,
  NodeData,
  WorkflowStatus,
  StepStatus,
  StepExecution,
} from "./types";
import { StepLibrary } from "./library";
import { StepNode } from "./nodes";
import { Toolbar } from "./toolbar";
import { StepDetails } from "./step-details";
import { useWorkflowWebSocket } from "./useWorkflowWebSocket";
import { workflowAPI } from "./api";
import { appContext } from "../../../hooks/provider";
import {
  convertToReactFlowNodes,
  convertToReactFlowEdges,
  addStepToWorkflow,
  saveNodePosition,
  removeNodePosition,
  calculateNodePosition,
} from "./utils";
import { Component } from "../../types/datamodel";
import { MonacoEditor } from "../monaco";
import debounce from "lodash.debounce";

// Custom node types
const nodeTypes: NodeTypes = {
  step: StepNode,
};

interface WorkflowBuilderProps {
  workflow: Workflow;
  onChange?: (workflow: Partial<Workflow>) => void;
  onSave?: (workflow: Partial<Workflow>) => void;
  onDirtyStateChange?: (isDirty: boolean) => void;
}

export const WorkflowBuilder: React.FC<WorkflowBuilderProps> = ({
  workflow,
  onChange,
  onSave,
  onDirtyStateChange,
}) => {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<NodeData>>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [isLibraryCompact, setIsLibraryCompact] = useState(false);
  const [showMiniMap, setShowMiniMap] = useState(false);
  const [showGrid, setShowGrid] = useState(true);
  const [isDirty, setIsDirty] = useState(false);
  const [selectedStep, setSelectedStep] = useState<StepConfig | null>(null);
  const [selectedStepExecution, setSelectedStepExecution] = useState<
    StepExecution | undefined
  >(undefined);
  const [stepDetailsOpen, setStepDetailsOpen] = useState(false);
  const [edgeType, setEdgeType] = useState<string>("smoothstep");
  const [isJsonMode, setIsJsonMode] = useState(false);
  const [workingCopy, setWorkingCopy] = useState<Workflow>(workflow);
  const editorRef = useRef(null);

  const [messageApi, contextHolder] = message.useMessage();
  const { user } = useContext(appContext);

  // WebSocket integration for real-time workflow execution
  const {
    connectionStatus,
    executionState,
    startWorkflow,
    stopWorkflow,
    disconnect,
    resetState,
  } = useWorkflowWebSocket();

  // Notify parent of dirty state changes
  useEffect(() => {
    onDirtyStateChange?.(isDirty);
  }, [isDirty, onDirtyStateChange]);

  // Update working copy when workflow changes
  useEffect(() => {
    setWorkingCopy(workflow);
  }, [workflow]);

  // Handle JSON changes
  const handleJsonChange = useCallback(
    debounce((value: string) => {
      try {
        const updatedConfig = JSON.parse(value);
        const updatedWorkflow = {
          ...workingCopy,
          config: updatedConfig,
        };
        setWorkingCopy(updatedWorkflow);
        onChange?.(updatedWorkflow);
        setIsDirty(true);
      } catch (err) {
        console.error("Invalid JSON", err);
      }
    }, 1000),
    [onChange, workingCopy]
  );

  // Update node execution status and edge animations
  useEffect(() => {
    // If no execution state or workflow is cancelled, reset all nodes and edges to initial state
    if (
      !executionState.execution ||
      executionState.status === WorkflowStatus.CANCELLED
    ) {
      setNodes((currentNodes) =>
        currentNodes.map((node) => ({
          ...node,
          data: {
            ...node.data,
            executionStatus: undefined, // No status before execution or when cancelled
            executionData: undefined,
          },
        }))
      );

      setEdges((currentEdges) =>
        currentEdges.map((edge) => ({
          ...edge,
          style: { stroke: "#6b7280", strokeWidth: 2 }, // Default style
          animated: false,
        }))
      );
      return;
    }

    setNodes((currentNodes) =>
      currentNodes.map((node) => {
        const stepExecution =
          executionState.execution?.step_executions[node.id];

        return {
          ...node,
          data: {
            ...node.data,
            executionStatus: stepExecution?.status || StepStatus.PENDING,
            executionData: stepExecution,
          },
        };
      })
    );

    // Update edge animations based on execution state
    setEdges((currentEdges) =>
      currentEdges.map((edge) => {
        const fromStepExecution =
          executionState.execution?.step_executions[edge.source];
        const toStepExecution =
          executionState.execution?.step_executions[edge.target];

        let edgeStyle = { ...edge.style };
        let animated = false;

        // Animate edge if source is completed and target is running
        if (
          fromStepExecution?.status === StepStatus.COMPLETED &&
          toStepExecution?.status === StepStatus.RUNNING
        ) {
          edgeStyle = {
            stroke: "#3b82f6",
            strokeWidth: 3,
            strokeDasharray: "5,5",
          };
          animated = true;
        }
        // Show completed edge if both source and target are completed
        else if (
          fromStepExecution?.status === StepStatus.COMPLETED &&
          toStepExecution?.status === StepStatus.COMPLETED
        ) {
          edgeStyle = {
            stroke: "#10b981",
            strokeWidth: 2,
          };
        }
        // Show failed edge if target failed
        else if (toStepExecution?.status === StepStatus.FAILED) {
          edgeStyle = {
            stroke: "#ef4444",
            strokeWidth: 2,
            strokeDasharray: "3,3",
          };
        }
        // Show cancelled edge if target cancelled
        else if (toStepExecution?.status === StepStatus.CANCELLED) {
          edgeStyle = {
            stroke: "#f97316",
            strokeWidth: 2,
            strokeDasharray: "5,5",
          };
        }

        return {
          ...edge,
          style: edgeStyle,
          animated,
        };
      })
    );
  }, [executionState.execution, setNodes, setEdges]);

  // Handle workflow execution status changes - only show completion/failure toasts
  useEffect(() => {
    switch (executionState.status) {
      case WorkflowStatus.COMPLETED:
        messageApi.success("Workflow completed successfully!");
        break;
      case WorkflowStatus.FAILED:
        messageApi.error(
          `Workflow failed: ${executionState.error || "Unknown error"}`
        );
        break;
      case WorkflowStatus.CANCELLED:
        messageApi.info("Workflow execution was cancelled");
        break;
      default:
        break;
    }
  }, [executionState.status, executionState.error, messageApi]);

  // Clean up WebSocket connection on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  // Helper function to get workflow status indicator configuration
  const getWorkflowStatusConfig = (status: WorkflowStatus) => {
    switch (status) {
      case WorkflowStatus.RUNNING:
        return {
          icon: Loader2,
          text: "Running",
          color: "text-blue-500",
          bgColor: "bg-blue-50",
          borderColor: "border-blue-200",
          animate: "animate-spin",
        };
      case WorkflowStatus.COMPLETED:
        return {
          icon: CheckCircle,
          text: "Completed",
          color: "text-green-500",
          bgColor: "bg-green-50",
          borderColor: "border-green-200",
          animate: "",
        };
      case WorkflowStatus.FAILED:
        return {
          icon: XCircle,
          text: "Failed",
          color: "text-red-500",
          bgColor: "bg-red-50",
          borderColor: "border-red-200",
          animate: "",
        };
      case WorkflowStatus.CANCELLED:
        return {
          icon: AlertCircle,
          text: "Cancelled",
          color: "text-orange-500",
          bgColor: "bg-orange-50",
          borderColor: "border-orange-200",
          animate: "",
        };
      default:
        return {
          icon: Clock,
          text: "Ready",
          color: "text-gray-500",
          bgColor: "bg-gray-50",
          borderColor: "border-gray-200",
          animate: "",
        };
    }
  };

  const onConnect = useCallback(
    (params: Connection) => {
      setEdges((eds) =>
        addEdge(
          {
            ...params,
            type: edgeType,
          },
          eds
        )
      );

      const newEdge = {
        id: `edge-${params.source}-${params.target}-${Date.now()}`,
        from_step: params.source!,
        to_step: params.target!,
      };

      const updatedConfig = {
        ...workflow.config.config,
        edges: [...(workflow.config.config.edges || []), newEdge],
      };

      onChange?.({
        ...workflow,
        config: {
          ...workflow.config,
          config: updatedConfig,
        },
      });

      setIsDirty(true);
      messageApi.success("Edge added successfully");
    },
    [workflow.config, setEdges, onChange, messageApi, edgeType]
  );

  const onNodeDragStop = useCallback(
    (event: any, node: Node) => {
      if (workflow.id) {
        const workflowId =
          typeof workflow.id === "string"
            ? parseInt(workflow.id, 10)
            : workflow.id;

        if (!isNaN(workflowId)) {
          saveNodePosition(workflowId, node.id, node.position);
          setIsDirty(true);
        }
      }
    },
    [workflow.id]
  );

  const handleAddStep = useCallback(
    (step: Component<StepConfig>) => {
      const position = calculateNodePosition(
        workflow.config.config.steps?.length || 0,
        (workflow.config.config.steps?.length || 0) + 1
      );

      if (workflow.id) {
        const workflowId =
          typeof workflow.id === "string"
            ? parseInt(workflow.id, 10)
            : workflow.id;

        if (!isNaN(workflowId)) {
          saveNodePosition(workflowId, step.config.step_id, position);
        }
      }

      const updatedConfig = addStepToWorkflow(workflow.config.config, step);

      const newWorkflow = {
        ...workflow,
        config: {
          ...workflow.config,
          config: updatedConfig,
        },
      };

      onChange?.(newWorkflow);
      setIsDirty(true);
      messageApi.success(`Added ${step.config.metadata.name} to workflow`);
    },
    [workflow, onChange, messageApi]
  );

  const handleDeleteStep = useCallback(
    (stepId: string) => {
      const updatedConfig = {
        ...workflow.config.config,
        steps:
          workflow.config.config.steps?.filter(
            (s) => s.config.step_id !== stepId
          ) || [],
        edges:
          workflow.config.config.edges?.filter(
            (e) => e.from_step !== stepId && e.to_step !== stepId
          ) || [],
        start_step_id:
          workflow.config.config.start_step_id === stepId
            ? undefined
            : workflow.config.config.start_step_id,
      };

      const stepName =
        workflow.config.config.steps?.find((s) => s.config.step_id === stepId)
          ?.config.metadata.name || "Step";

      if (workflow.id) {
        const workflowId =
          typeof workflow.id === "string"
            ? parseInt(workflow.id, 10)
            : workflow.id;

        if (!isNaN(workflowId)) {
          removeNodePosition(workflowId, stepId);
        }
      }

      onChange?.({
        ...workflow,
        config: {
          ...workflow.config,
          config: updatedConfig,
        },
      });
      setIsDirty(true);
      messageApi.success(`Removed ${stepName} from workflow`);
    },
    [workflow, onChange, messageApi]
  );

  const onEdgesDelete = useCallback(
    (edgesToDelete: Edge[]) => {
      const edgeIdsToDelete = new Set(edgesToDelete.map((edge) => edge.id));
      const updatedConfig = {
        ...workflow.config.config,
        edges:
          workflow.config.config.edges?.filter(
            (edge) => !edgeIdsToDelete.has(edge.id)
          ) || [],
      };

      onChange?.({
        ...workflow,
        config: {
          ...workflow.config,
          config: updatedConfig,
        },
      });

      setIsDirty(true);
      messageApi.success(`Deleted ${edgesToDelete.length} edge(s)`);
    },
    [workflow, onChange, messageApi]
  );

  // Initialize nodes and edges from workflow - positions come from localStorage
  useEffect(() => {
    const workflowId =
      typeof workflow.id === "string"
        ? parseInt(workflow.id, 10)
        : workflow.id || 0;

    const flowNodes = convertToReactFlowNodes(
      workflow.config.config,
      workflowId,
      handleDeleteStep,
      handleStepClick
    );
    const flowEdges = convertToReactFlowEdges(workflow.config.config, edgeType);
    setNodes(flowNodes);
    setEdges(flowEdges);
  }, [
    workflow.config,
    workflow.id,
    edgeType,
    setNodes,
    setEdges,
    handleDeleteStep,
  ]);

  const handleSaveWorkflow = useCallback(async () => {
    try {
      await onSave?.(workflow);
      setIsDirty(false);
      messageApi.success("Workflow saved successfully");
    } catch (error) {
      console.error("Error saving workflow:", error);
      messageApi.error("Failed to save workflow");
    }
  }, [workflow, onSave, messageApi]);

  const handleRunWorkflow = useCallback(async () => {
    if (!user?.id) {
      messageApi.error("User not authenticated");
      return;
    }

    if (!workflow.config.config.steps?.length) {
      messageApi.error("Workflow must have at least one step");
      return;
    }

    try {
      messageApi.loading("Starting workflow execution...", 0);

      // Reset WebSocket state first
      resetState();

      // Reset all node and edge states to initial state
      setNodes((currentNodes) =>
        currentNodes.map((node) => ({
          ...node,
          data: {
            ...node.data,
            executionStatus: undefined, // Reset to no status
          },
        }))
      );

      setEdges((currentEdges) =>
        currentEdges.map((edge) => ({
          ...edge,
          style: { stroke: "#6b7280", strokeWidth: 2 }, // Reset to default style
          animated: false,
        }))
      );

      // Create a workflow run
      const runResponse = await workflowAPI.createWorkflowRun(
        undefined, // workflowId - use config instead for real-time execution
        workflow.config
      );

      const { run_id, workflow_config } = runResponse.data;

      // Start WebSocket-based execution
      startWorkflow(run_id, workflow_config, {
        // Optional initial input - could be made configurable
        message: "Starting workflow execution",
      });

      messageApi.destroy(); // Clear loading message
      messageApi.success("Workflow execution started!");
    } catch (error) {
      messageApi.destroy();
      console.error("Error starting workflow:", error);
      messageApi.error("Failed to start workflow execution");
    }
  }, [
    user?.id,
    workflow.config,
    startWorkflow,
    resetState,
    messageApi,
    setNodes,
    setEdges,
  ]);

  const handleStopWorkflow = useCallback(() => {
    stopWorkflow();
    messageApi.info("Stopping workflow execution...");
  }, [stopWorkflow, messageApi]);

  const handleLayoutNodes = useCallback(() => {
    if (workflow.id) {
      const workflowId =
        typeof workflow.id === "string"
          ? parseInt(workflow.id, 10)
          : workflow.id;

      if (isNaN(workflowId)) return;

      workflow.config.config.steps?.forEach((step, index) => {
        const position = calculateNodePosition(
          index,
          workflow.config.config.steps?.length || 0
        );
        saveNodePosition(workflowId, step.config.step_id, position);
      });

      const flowNodes = convertToReactFlowNodes(
        workflow.config.config,
        workflowId,
        handleDeleteStep,
        handleStepClick
      );
      setNodes(flowNodes);

      messageApi.success("Nodes arranged automatically");
    }
  }, [workflow, messageApi, handleDeleteStep, setNodes]);

  const handleStepClick = useCallback(
    (step: StepConfig, executionData?: StepExecution) => {
      setSelectedStep(step);
      setSelectedStepExecution(executionData);
      setStepDetailsOpen(true);
    },
    []
  );

  const handleStepSave = useCallback(
    (updatedStep: StepConfig) => {
      // Update the step in the workflow
      const updatedConfig = {
        ...workflow.config.config,
        steps:
          workflow.config.config.steps?.map((s) =>
            s.config.step_id === updatedStep.step_id
              ? { ...s, config: updatedStep }
              : s
          ) || [],
      };

      const updatedWorkflow = {
        ...workflow,
        config: {
          ...workflow.config,
          config: updatedConfig,
        },
      };

      onChange?.(updatedWorkflow);
      setIsDirty(true);
      messageApi.success("Step configuration updated");
    },
    [workflow, onChange, messageApi]
  );

  const handleEdgeTypeChange = useCallback(
    (newEdgeType: string) => {
      setEdgeType(newEdgeType);
      setEdges((currentEdges) =>
        currentEdges.map((edge) => ({
          ...edge,
          type: newEdgeType,
        }))
      );
      setIsDirty(true);
    },
    [setEdges]
  );

  // Handle keyboard events for node deletion
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Delete" || event.key === "Backspace") {
        const selectedNodes = nodes.filter((node) => node.selected);
        selectedNodes.forEach((node) => {
          handleDeleteStep(node.id);
        });
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [nodes, handleDeleteStep]);

  return (
    <div className="h-full flex">
      {contextHolder}

      {/* CSS for edge animations */}
      <style>{`
        @keyframes dash {
          to {
            stroke-dashoffset: -10;
          }
        }
        .react-flow__edge-path {
          animation: dash 1s linear infinite;
        }
      `}</style>

      {/* Main Canvas */}
      <div className="flex-1 relative">
        {/* Top Panel - Workflow Info (Always Visible) */}
        <div className="absolute top-4 left-4 z-10">
          <div className="bg-primary rounded border border-secondary p-3 shadow-sm">
            <div className="text-sm">
              <div className="flex items-center justify-between mb-2">
                <div className="font-medium text-primary">
                  {workflow.config.config.name || "Workflow"}
                </div>
                <div className="flex items-center gap-2">
                  {/* JSON Mode Toggle */}
                  <Switch
                    onChange={() => {
                      setIsJsonMode(!isJsonMode);
                    }}
                    className="mr-2"
                    defaultChecked={!isJsonMode}
                    checkedChildren={
                      <div className="text-xs">
                        <Cable className="w-3 h-3 inline-block mt-1 mr-1" />
                      </div>
                    }
                    unCheckedChildren={
                      <div className="text-xs">
                        <Code2 className="w-3 h-3 mt-1 inline-block mr-1" />
                      </div>
                    }
                  />
                  {/* Workflow Status Indicator */}
                  {executionState.status !== WorkflowStatus.CREATED && (
                    <div className="flex items-center gap-2">
                      {(() => {
                        const statusConfig = getWorkflowStatusConfig(
                          executionState.status
                        );
                        const IconComponent = statusConfig.icon;
                        return (
                          <div
                            className={`flex items-center gap-1.5 px-2 py-1 rounded-full border text-xs font-medium ${statusConfig.bgColor} ${statusConfig.borderColor} ${statusConfig.color}`}
                          >
                            <IconComponent
                              size={14}
                              className={statusConfig.animate}
                            />
                            <span>{statusConfig.text}</span>
                          </div>
                        );
                      })()}
                    </div>
                  )}
                </div>
              </div>
              <div className="text-secondary text-xs">
                Sequential execution with data flow between steps
              </div>
              <div className="text-xs text-secondary mt-1">
                {workflow.config.config.steps?.length || 0} steps,{" "}
                {workflow.config.config.edges?.length || 0} connections
              </div>

              {/* Results Panel: Compact, live-updating step outputs */}
              {executionState.execution &&
                workflow.config.config.steps?.length &&
                (() => {
                  // Filter steps with actual results (output or error)
                  const stepsWithResults = workflow.config.config.steps.filter(
                    (step) => {
                      const stepExec =
                        executionState.execution?.step_executions[
                          step.config.step_id
                        ];
                      return (
                        stepExec &&
                        stepExec.status !== StepStatus.PENDING &&
                        (stepExec.output_data || stepExec.error)
                      );
                    }
                  );
                  if (!stepsWithResults.length) return null;
                  return (
                    <div className="mt-2">
                      <div className="font-semibold text-xs mb-1">
                        Step Results
                      </div>
                      <div style={{ maxHeight: 160, overflowY: "auto" }}>
                        {stepsWithResults.map((step) => {
                          const stepId = step.config.step_id;
                          const stepName = step.config.metadata.name || stepId;
                          const stepExec =
                            executionState.execution?.step_executions[stepId];
                          if (!stepExec) return null;
                          // Status icon config
                          const statusConfig = (() => {
                            switch (stepExec.status) {
                              case StepStatus.RUNNING:
                                return {
                                  icon: Loader2,
                                  color: "text-blue-500",
                                  animate: "animate-spin",
                                  text: "Running",
                                };
                              case StepStatus.COMPLETED:
                                return {
                                  icon: CheckCircle,
                                  color: "text-green-500",
                                  animate: "",
                                  text: "Completed",
                                };
                              case StepStatus.FAILED:
                                return {
                                  icon: XCircle,
                                  color: "text-red-500",
                                  animate: "",
                                  text: "Failed",
                                };
                              case StepStatus.CANCELLED:
                                return {
                                  icon: AlertCircle,
                                  color: "text-orange-500",
                                  animate: "",
                                  text: "Cancelled",
                                };
                              case StepStatus.SKIPPED:
                                return {
                                  icon: AlertCircle,
                                  color: "text-orange-500",
                                  animate: "",
                                  text: "Skipped",
                                };
                              default:
                                return {
                                  icon: Clock,
                                  color: "text-gray-500",
                                  animate: "",
                                  text: "Pending",
                                };
                            }
                          })();
                          const Icon = statusConfig.icon;
                          // Output preview
                          let outputPreview = "";
                          if (stepExec.output_data) {
                            try {
                              outputPreview = JSON.stringify(
                                stepExec.output_data
                              );
                            } catch {
                              outputPreview = String(stepExec.output_data);
                            }
                            if (outputPreview.length > 60)
                              outputPreview =
                                outputPreview.slice(0, 60) + "...";
                          } else if (stepExec.error) {
                            outputPreview = `Error: ${stepExec.error.slice(
                              0,
                              60
                            )}${stepExec.error.length > 60 ? "..." : ""}`;
                          } else {
                            outputPreview = "";
                          }
                          return (
                            <div
                              key={stepId}
                              className="flex items-center gap-2 py-1 px-2 rounded hover:bg-tertiary transition cursor-pointer group"
                            >
                              <Icon
                                size={14}
                                className={`${statusConfig.color} ${statusConfig.animate}`}
                              />
                              <span
                                className="truncate flex-1 text-xs"
                                title={stepName}
                              >
                                {stepName}
                              </span>
                              {outputPreview && (
                                <span
                                  className="truncate text-xs text-secondary max-w-[120px]"
                                  title={outputPreview}
                                >
                                  {outputPreview}
                                </span>
                              )}
                              {/* Only show View button if there is output or error */}
                              {(stepExec.output_data || stepExec.error) && (
                                <Button
                                  size="small"
                                  type="link"
                                  className="p-0 text-accent group-hover:underline"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    setSelectedStep(step.config);
                                    setSelectedStepExecution(stepExec);
                                    setStepDetailsOpen(true);
                                  }}
                                >
                                  View
                                </Button>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  );
                })()}
            </div>
          </div>
        </div>

        {isJsonMode ? (
          <div className="h-full">
            <MonacoEditor
              editorRef={editorRef}
              value={JSON.stringify(workingCopy.config, null, 2)}
              onChange={handleJsonChange}
              language="json"
              minimap={true}
            />
          </div>
        ) : (
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            onNodeDragStop={onNodeDragStop}
            onEdgesDelete={onEdgesDelete}
            nodeTypes={nodeTypes}
            fitView
            minZoom={0.1}
            maxZoom={2}
            defaultEdgeOptions={{
              animated: false,
              style: { stroke: "#6b7280", strokeWidth: 2 },
            }}
          >
            <Background
              variant={BackgroundVariant.Dots}
              gap={20}
              size={1}
              color="#e0e0e0"
            />

            {showMiniMap && (
              <MiniMap
                nodeStrokeColor="#666"
                nodeColor="#fff"
                maskColor="rgba(0,0,0,0.1)"
                position="bottom-right"
              />
            )}
          </ReactFlow>
        )}

        {/* Toolbar - Only show in visual mode */}
        {!isJsonMode && (
          <Toolbar
            isDirty={isDirty}
            onSave={handleSaveWorkflow}
            onRun={handleRunWorkflow}
            onStop={handleStopWorkflow}
            onAutoLayout={handleLayoutNodes}
            onToggleMiniMap={() => setShowMiniMap(!showMiniMap)}
            onToggleGrid={() => setShowGrid(!showGrid)}
            showMiniMap={showMiniMap}
            showGrid={showGrid}
            disabled={(workflow.config.config.steps?.length || 0) === 0}
            edgeType={edgeType}
            onEdgeTypeChange={handleEdgeTypeChange}
            workflowStatus={executionState.status}
            isConnected={connectionStatus.isConnected}
          />
        )}

        {/* Empty State - Only show in visual mode */}
        {!isJsonMode && (workflow.config.config.steps?.length || 0) === 0 && (
          <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
            <div className="text-center text-secondary">
              <div className="text-lg font-medium mb-2">
                Start Building Your Workflow
              </div>
              <div className="text-sm">
                Click steps from the library to add them to your workflow
              </div>
              {isLibraryCompact && (
                <div className="text-xs text-accent mt-2">
                  Expand the library to browse all available steps
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Agent Library Sidebar */}
      {!isJsonMode && (
        <div
          className={`${
            isLibraryCompact ? "w-12" : "w-64"
          } border-l border-secondary bg-tertiary transition-all duration-200`}
        >
          <StepLibrary
            onAddStep={handleAddStep}
            isCompact={isLibraryCompact}
            onToggleCompact={() => setIsLibraryCompact(!isLibraryCompact)}
          />
        </div>
      )}

      {/* Step Details Modal */}
      {selectedStep && (
        <StepDetails
          step={selectedStep}
          executionData={selectedStepExecution}
          isOpen={stepDetailsOpen}
          onClose={() => setStepDetailsOpen(false)}
        />
      )}
    </div>
  );
};

export default WorkflowBuilder;
