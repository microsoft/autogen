//team/builder/builder.tsx
import React, { useCallback, useEffect, useRef, useState } from "react";
import {
  DndContext,
  useSensor,
  useSensors,
  PointerSensor,
  DragEndEvent,
  DragOverEvent,
} from "@dnd-kit/core";
import {
  ReactFlow,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Background,
  MiniMap,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Button, Layout, message, Modal, Switch, Tooltip } from "antd";
import { Cable, Code2, Download, Save } from "lucide-react";
import { useTeamBuilderStore } from "./store";
import { ComponentLibrary } from "./library";
import { ComponentTypes, Team } from "../../../types/datamodel";
import { CustomNode, CustomEdge, DragItem } from "./types";
import { edgeTypes, nodeTypes } from "./nodes";

// import builder css
import "./builder.css";
import TeamBuilderToolbar from "./toolbar";
import { MonacoEditor } from "../../monaco";
import { NodeEditor } from "./node-editor/node-editor";
import debounce from "lodash.debounce";

const { Sider, Content } = Layout;

interface TeamBuilderProps {
  team: Team;
  onChange?: (team: Partial<Team>) => void;
  onDirtyStateChange?: (isDirty: boolean) => void;
}

export const TeamBuilder: React.FC<TeamBuilderProps> = ({
  team,
  onChange,
  onDirtyStateChange,
}) => {
  // Replace store state with React Flow hooks
  const [nodes, setNodes, onNodesChange] = useNodesState<CustomNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<CustomEdge>([]);
  const [isJsonMode, setIsJsonMode] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showGrid, setShowGrid] = useState(true);
  const [showMiniMap, setShowMiniMap] = useState(true);
  // const [isDirty, setIsDirty] = useState(false);
  const editorRef = useRef(null);
  const [messageApi, contextHolder] = message.useMessage();

  const {
    undo,
    redo,
    loadFromJson,
    syncToJson,
    addNode,
    layoutNodes,
    resetHistory,
    history,
    updateNode,
    selectedNodeId,
    setSelectedNode,
  } = useTeamBuilderStore();

  const currentHistoryIndex = useTeamBuilderStore(
    (state) => state.currentHistoryIndex
  );

  // Compute isDirty based on the store value
  const isDirty = currentHistoryIndex > 0;

  // Compute undo/redo capability from history state
  const canUndo = currentHistoryIndex > 0;
  const canRedo = currentHistoryIndex < history.length - 1;

  const onConnect = useCallback(
    (params: Connection) =>
      setEdges((eds: CustomEdge[]) => addEdge(params, eds)),
    [setEdges]
  );

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8,
      },
    })
  );

  // Need to notify parent whenever isDirty changes
  React.useEffect(() => {
    onDirtyStateChange?.(isDirty);
  }, [isDirty, onDirtyStateChange]);

  // Add beforeunload handler when dirty
  React.useEffect(() => {
    if (isDirty) {
      const handleBeforeUnload = (e: BeforeUnloadEvent) => {
        e.preventDefault();
        e.returnValue = "";
      };
      window.addEventListener("beforeunload", handleBeforeUnload);
      return () =>
        window.removeEventListener("beforeunload", handleBeforeUnload);
    }
  }, [isDirty]);

  // Load initial config
  React.useEffect(() => {
    if (team?.component) {
      const { nodes: initialNodes, edges: initialEdges } = loadFromJson(
        team.component
      );
      setNodes(initialNodes);
      setEdges(initialEdges);
    }
  }, [team, setNodes, setEdges]);

  // Handle JSON changes
  const handleJsonChange = useCallback(
    debounce((value: string) => {
      try {
        const config = JSON.parse(value);
        // Always consider JSON edits as changes that should affect isDirty state
        loadFromJson(config, false);
        // Force history update even if nodes/edges appear same
        useTeamBuilderStore.getState().addToHistory();
      } catch (error) {
        console.error("Invalid JSON:", error);
      }
    }, 1000),
    [loadFromJson]
  );

  // Cleanup debounced function
  useEffect(() => {
    return () => {
      handleJsonChange.cancel();
    };
  }, [handleJsonChange]);

  // Handle save
  const handleSave = useCallback(async () => {
    try {
      const component = syncToJson();
      if (!component) {
        throw new Error("Unable to generate valid configuration");
      }

      if (onChange) {
        console.log("Saving team configuration", component);
        const teamData: Partial<Team> = team
          ? {
              ...team,
              component,
              created_at: undefined,
              updated_at: undefined,
            }
          : { component };
        await onChange(teamData);
        resetHistory();
      }
    } catch (error) {
      messageApi.error(
        error instanceof Error
          ? error.message
          : "Failed to save team configuration"
      );
    }
  }, [syncToJson, onChange, resetHistory]);

  const handleToggleFullscreen = useCallback(() => {
    setIsFullscreen((prev) => !prev);
  }, []);

  React.useEffect(() => {
    if (!isFullscreen) return;
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setIsFullscreen(false);
      }
    };
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [isFullscreen]);

  React.useEffect(() => {
    const unsubscribe = useTeamBuilderStore.subscribe((state) => {
      setNodes(state.nodes);
      setEdges(state.edges);
      // console.log("nodes updated", state);
    });
    return unsubscribe;
  }, [setNodes, setEdges]);

  const validateDropTarget = (
    draggedType: ComponentTypes,
    targetType: ComponentTypes
  ): boolean => {
    const validTargets: Record<ComponentTypes, ComponentTypes[]> = {
      model: ["team", "agent"],
      tool: ["agent"],
      agent: ["team"],
      team: [],
      termination: ["team"],
    };
    return validTargets[draggedType]?.includes(targetType) || false;
  };

  const handleDragOver = (event: DragOverEvent) => {
    const { active, over } = event;
    if (!over?.id || !active.data.current) return;

    const draggedType = active.data.current.type;
    const targetNode = nodes.find((node) => node.id === over.id);
    if (!targetNode) return;

    const isValid = validateDropTarget(
      draggedType,
      targetNode.data.component.component_type
    );
    // Add visual feedback class to target node
    if (isValid) {
      targetNode.className = "drop-target-valid";
    } else {
      targetNode.className = "drop-target-invalid";
    }
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (!over || !active.data?.current?.current) return;

    const draggedItem = active.data.current.current;
    const dropZoneId = over.id as string;

    const [nodeId] = dropZoneId.split("@@@");
    // Find target node
    const targetNode = nodes.find((node) => node.id === nodeId);
    if (!targetNode) return;

    // Validate drop
    const isValid = validateDropTarget(
      draggedItem.type,
      targetNode.data.component.component_type
    );
    if (!isValid) return;

    const position = {
      x: event.delta.x,
      y: event.delta.y,
    };

    // Pass both new node data AND target node id
    addNode(position, draggedItem.config, nodeId);
  };

  const onDragStart = (item: DragItem) => {
    // We can add any drag start logic here if needed
  };
  return (
    <div>
      {contextHolder}
      <div className="flex gap-2 text-xs rounded border-dashed border p-2 mb-2 items-center">
        <div className="flex-1">
          <Switch
            onChange={() => {
              setIsJsonMode(!isJsonMode);
            }}
            className="mr-2"
            // size="small"
            defaultChecked={!isJsonMode}
            checkedChildren=<div className=" text-xs">
              <Cable className="w-3 h-3 inline-block mt-1 mr-1" />
            </div>
            unCheckedChildren=<div className=" text-xs">
              <Code2 className="w-3 h-3 mt-1 inline-block mr-1" />
            </div>
          />
          {isJsonMode ? (
            "JSON "
          ) : (
            <>
              Visual builder{" "}
              {/* <span className="text-xs text-orange-500  border border-orange-400 rounded-lg px-2 mx-1">
              {" "}
              experimental{" "}
            </span> */}
            </>
          )}{" "}
          mode{" "}
          <span className="text-xs text-orange-500 ml-1 underline">
            {" "}
            (experimental)
          </span>
        </div>
        <div>
          <Tooltip title="Download Team">
            <Button
              type="text"
              icon={<Download size={18} />}
              className="p-1.5 hover:bg-primary/10 rounded-md text-primary/75 hover:text-primary"
              onClick={() => {
                const json = JSON.stringify(syncToJson(), null, 2);
                const blob = new Blob([json], { type: "application/json" });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = "team-config.json";
                a.click();
                URL.revokeObjectURL(url);
              }}
            />
          </Tooltip>

          <Tooltip title="Save Changes">
            <Button
              type="text"
              icon={
                <div className="relative">
                  <Save size={18} />
                  {isDirty && (
                    <div className="absolute top-0 right-0 w-2 h-2 bg-red-500 rounded-full"></div>
                  )}
                </div>
              }
              className="p-1.5 hover:bg-primary/10 rounded-md text-primary/75 hover:text-primary disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={handleSave}
              // disabled={!isDirty}
            />
          </Tooltip>
        </div>
      </div>
      <DndContext
        sensors={sensors}
        onDragEnd={handleDragEnd}
        onDragOver={handleDragOver}
      >
        <Layout className=" relative bg-primary  h-[calc(100vh-239px)] rounded">
          {!isJsonMode && <ComponentLibrary />}

          <Layout className="bg-primary rounded">
            <Content className="relative rounded bg-tertiary  ">
              <div
                className={`w-full h-full transition-all duration-200 ${
                  isFullscreen
                    ? "fixed inset-4 z-50 shadow bg-tertiary  backdrop-blur-sm"
                    : ""
                }`}
              >
                {isJsonMode ? (
                  <MonacoEditor
                    value={JSON.stringify(syncToJson(), null, 2)}
                    onChange={handleJsonChange}
                    editorRef={editorRef}
                    language="json"
                    minimap={false}
                  />
                ) : (
                  <ReactFlow
                    nodes={nodes}
                    edges={edges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    onConnect={onConnect}
                    // onNodeClick={(_, node) => setSelectedNode(node.id)}
                    nodeTypes={nodeTypes}
                    edgeTypes={edgeTypes}
                    onDrop={(event) => event.preventDefault()}
                    onDragOver={(event) => event.preventDefault()}
                    className="rounded"
                    fitView
                    fitViewOptions={{ padding: 10 }}
                  >
                    {showGrid && <Background />}
                    {showMiniMap && <MiniMap />}
                  </ReactFlow>
                )}
              </div>
              {isFullscreen && (
                <div
                  className="fixed inset-0 -z-10 bg-background bg-opacity-80 backdrop-blur-sm"
                  onClick={handleToggleFullscreen}
                />
              )}
              <TeamBuilderToolbar
                isJsonMode={isJsonMode}
                isFullscreen={isFullscreen}
                showGrid={showGrid}
                onToggleMiniMap={() => setShowMiniMap(!showMiniMap)}
                canUndo={canUndo}
                canRedo={canRedo}
                isDirty={isDirty}
                onToggleView={() => setIsJsonMode(!isJsonMode)}
                onUndo={undo}
                onRedo={redo}
                onSave={handleSave}
                onToggleGrid={() => setShowGrid(!showGrid)}
                onToggleFullscreen={handleToggleFullscreen}
                onAutoLayout={layoutNodes}
              />
            </Content>
          </Layout>

          <NodeEditor
            node={nodes.find((n) => n.id === selectedNodeId) || null}
            onUpdate={(updates) => {
              if (selectedNodeId) {
                console.log("updating node", selectedNodeId, updates);
                updateNode(selectedNodeId, updates);
                handleSave();
              }
            }}
            onClose={() => setSelectedNode(null)}
          />
        </Layout>
      </DndContext>
    </div>
  );
};
