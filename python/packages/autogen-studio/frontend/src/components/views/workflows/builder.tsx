import React, { useCallback, useEffect, useState } from "react";
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
import { message, Drawer, Button } from "antd";
import { Workflow, Step, NodeData } from "./types";
import { StepLibrary } from "./library";
import { StepNode } from "./nodes";
import { Toolbar } from "./toolbar";
import {
  convertToReactFlowNodes,
  convertToReactFlowEdges,
  addStepToWorkflow,
  saveNodePosition,
  removeNodePosition,
  calculateNodePosition,
} from "./utils";

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
  const [selectedStep, setSelectedStep] = useState<Step | null>(null);
  const [stepDrawerOpen, setStepDrawerOpen] = useState(false);
  const [edgeType, setEdgeType] = useState<string>("smoothstep");

  const [messageApi, contextHolder] = message.useMessage();

  // Notify parent of dirty state changes
  useEffect(() => {
    onDirtyStateChange?.(isDirty);
  }, [isDirty, onDirtyStateChange]);

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
        ...workflow.config,
        edges: [...workflow.config.edges, newEdge],
      };

      onChange?.({
        ...workflow,
        config: updatedConfig,
      });

      setIsDirty(true);
      messageApi.success("Edge added successfully");
    },
    [workflow.config, setEdges, onChange, messageApi, edgeType]
  );

  const onNodeDragStop = useCallback(
    (event: any, node: Node) => {
      if (workflow.id) {
        saveNodePosition(workflow.id, node.id, node.position);
        setIsDirty(true);
      }
    },
    [workflow.id]
  );

  const handleAddStep = useCallback(
    (step: Step) => {
      const position = calculateNodePosition(
        workflow.config.steps.length,
        workflow.config.steps.length + 1
      );

      if (workflow.id) {
        saveNodePosition(workflow.id, step.id, position);
      }

      const updatedConfig = addStepToWorkflow(workflow.config, step);

      const newWorkflow = {
        ...workflow,
        config: updatedConfig,
      };

      onChange?.(newWorkflow);
      setIsDirty(true);
      messageApi.success(`Added ${step.name} to workflow`);
    },
    [workflow, onChange, messageApi]
  );

  const handleDeleteStep = useCallback(
    (stepId: string) => {
      const updatedConfig = {
        ...workflow.config,
        steps: workflow.config.steps.filter((s) => s.id !== stepId),
        edges: workflow.config.edges.filter(
          (e) => e.from_step !== stepId && e.to_step !== stepId
        ),
        start_step_id:
          workflow.config.start_step_id === stepId
            ? undefined
            : workflow.config.start_step_id,
      };

      const stepName =
        workflow.config.steps.find((s) => s.id === stepId)?.name || "Step";

      if (workflow.id) {
        removeNodePosition(workflow.id, stepId);
      }

      onChange?.({
        ...workflow,
        config: updatedConfig,
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
        ...workflow.config,
        edges: workflow.config.edges.filter(
          (edge) => !edgeIdsToDelete.has(edge.id)
        ),
      };

      onChange?.({
        ...workflow,
        config: updatedConfig,
      });

      setIsDirty(true);
      messageApi.success(`Deleted ${edgesToDelete.length} edge(s)`);
    },
    [workflow, onChange, messageApi]
  );

  // Initialize nodes and edges from workflow - positions come from localStorage
  useEffect(() => {
    const flowNodes = convertToReactFlowNodes(
      workflow.config,
      workflow.id || "temp",
      handleDeleteStep
    );
    const flowEdges = convertToReactFlowEdges(workflow.config, edgeType);
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

  const handleRunWorkflow = useCallback(() => {
    messageApi.info("Workflow execution coming soon!");
  }, [messageApi]);

  const handleLayoutNodes = useCallback(() => {
    if (workflow.id) {
      workflow.config.steps.forEach((step, index) => {
        const position = calculateNodePosition(
          index,
          workflow.config.steps.length
        );
        saveNodePosition(workflow.id!, step.id, position);
      });

      const flowNodes = convertToReactFlowNodes(
        workflow.config,
        workflow.id,
        handleDeleteStep
      );
      setNodes(flowNodes);

      messageApi.success("Nodes arranged automatically");
    }
  }, [workflow, messageApi, handleDeleteStep, setNodes]);

  const handleStepClick = useCallback((step: Step) => {
    setSelectedStep(step);
    setStepDrawerOpen(true);
  }, []);

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

      {/* Main Canvas */}
      <div className="flex-1 relative">
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

          {/* Top Panel - Workflow Info */}
          <Panel
            position="top-left"
            className="bg-primary rounded border border-secondary p-2 shadow-sm"
          >
            <div className="text-sm">
              <div className="font-medium text-primary">
                {workflow.name || "Workflow"}
              </div>
              <div className="text-secondary text-xs">
                Sequential execution with data flow between steps
              </div>
              <div className="text-xs text-secondary mt-1">
                {workflow.config.steps.length} steps,{" "}
                {workflow.config.edges?.length || 0} connections
              </div>
            </div>
          </Panel>
        </ReactFlow>

        {/* Toolbar */}
        <Toolbar
          isDirty={isDirty}
          onSave={handleSaveWorkflow}
          onRun={handleRunWorkflow}
          onAutoLayout={handleLayoutNodes}
          onToggleMiniMap={() => setShowMiniMap(!showMiniMap)}
          onToggleGrid={() => setShowGrid(!showGrid)}
          showMiniMap={showMiniMap}
          showGrid={showGrid}
          disabled={workflow.config.steps.length === 0}
          edgeType={edgeType}
          onEdgeTypeChange={handleEdgeTypeChange}
        />

        {/* Empty State */}
        {workflow.config.steps.length === 0 && (
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
      <div
        className={`${
          isLibraryCompact ? "w-12" : "w-80"
        } border-l border-secondary bg-tertiary transition-all duration-200`}
      >
        <StepLibrary
          onAddStep={handleAddStep}
          isCompact={isLibraryCompact}
          onToggleCompact={() => setIsLibraryCompact(!isLibraryCompact)}
        />
      </div>

      {/* Agent Details Drawer */}
      <Drawer
        title={selectedStep?.name}
        placement="right"
        width={400}
        open={stepDrawerOpen}
        onClose={() => setStepDrawerOpen(false)}
      >
        {selectedStep && (
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium">Description</label>
              <div className="text-sm text-secondary mt-1">
                {selectedStep.description}
              </div>
            </div>

            <div>
              <label className="text-sm font-medium">System Message</label>
              <div className="text-sm text-secondary mt-1 p-2 bg-secondary rounded">
                {selectedStep.system_message}
              </div>
            </div>

            <div>
              <label className="text-sm font-medium">Model</label>
              <div className="text-sm text-secondary mt-1">
                {selectedStep.model}
              </div>
            </div>

            <div>
              <label className="text-sm font-medium">Tools</label>
              <div className="flex flex-wrap gap-1 mt-1">
                {selectedStep.tools?.map((tool, index) => (
                  <span
                    key={index}
                    className="px-2 py-1 text-xs bg-accent/10 text-accent rounded"
                  >
                    {tool}
                  </span>
                ))}
              </div>
            </div>

            <div className="pt-4 border-t">
              <Button type="primary" className="w-full">
                Test Step
              </Button>
            </div>
          </div>
        )}
      </Drawer>
    </div>
  );
};

export default WorkflowBuilder;
