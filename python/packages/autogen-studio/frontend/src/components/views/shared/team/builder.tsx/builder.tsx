import React, { useCallback } from "react";
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
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { Button, Layout, message } from "antd";
import { Undo2, Redo2, Save, LayoutIcon } from "lucide-react";
import { useTeamBuilderStore } from "./store";
import { ComponentLibrary } from "./components/library";
import { PropertyEditor } from "./components/property-editor";
import { ComponentTypes, TeamConfig } from "../../../../types/datamodel";
import { CustomNode, CustomEdge, DragItem, TeamBuilderState } from "./types";
import { edgeTypes, nodeTypes } from "./components/nodes";

// import builder css
import "./builder.css";

const { Sider, Content } = Layout;

interface TeamBuilderProps {
  team?: { config: TeamConfig };
  onChange?: (team: { config: TeamConfig }) => void;
}

export const TeamBuilder: React.FC<TeamBuilderProps> = ({ team, onChange }) => {
  // Replace store state with React Flow hooks
  const [nodes, setNodes, onNodesChange] = useNodesState<CustomNode>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<CustomEdge>([]);

  const {
    selectedNodeId,
    undo,
    redo,
    loadFromJson,
    syncToJson,
    addNode,
    updateNode,
    setSelectedNode,
    layoutNodes,
  } = useTeamBuilderStore();

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

  // Load initial config
  React.useEffect(() => {
    if (team?.config) {
      const { nodes: initialNodes, edges: initialEdges } = loadFromJson(
        team.config
      );
      setNodes(initialNodes);
      setEdges(initialEdges);
    }
  }, [team, setNodes, setEdges]);

  // Track selected node
  const selectedNode = React.useMemo<CustomNode | null>(
    () =>
      selectedNodeId
        ? nodes.find((node) => node.id === selectedNodeId) || null
        : null,
    [nodes, selectedNodeId]
  );

  const handleSave = React.useCallback(async () => {
    try {
      // Convert current nodes/edges back to config format
      const config = syncToJson();

      // Validation
      const teamNodes = nodes.filter((node) => node.data.type === "team");
      if (teamNodes.length === 0) {
        throw new Error("At least one team is required");
      }

      teamNodes.forEach((teamNode) => {
        const teamConfig = teamNode.data.config as TeamConfig;
        if (!teamConfig.participants || teamConfig.participants.length === 0) {
          throw new Error(
            `Team "${teamConfig.name}" must have at least one participant`
          );
        }
      });

      if (onChange && config) {
        await onChange({ config });
        message.success("Team configuration saved successfully");
      }
    } catch (error) {
      message.error(
        error instanceof Error
          ? error.message
          : "Failed to save team configuration"
      );
    }
  }, [nodes, syncToJson, onChange]);

  const handleNodeUpdate = React.useCallback(
    (updates: Partial<any>) => {
      if (selectedNodeId && updates) {
        updateNode(selectedNodeId, updates);
      }
    },
    [selectedNodeId, updateNode]
  );

  React.useEffect(() => {
    const unsubscribe = useTeamBuilderStore.subscribe((state) => {
      setNodes(state.nodes);
      setEdges(state.edges);
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
      termination: [],
    };
    return validTargets[draggedType]?.includes(targetType) || false;
  };

  const handleDragOver = (event: DragOverEvent) => {
    const { active, over } = event;
    if (!over?.id || !active.data.current) return;

    const draggedType = active.data.current.type;
    const targetNode = nodes.find((node) => node.id === over.id);
    if (!targetNode) return;

    const isValid = validateDropTarget(draggedType, targetNode.data.type);
    // Add visual feedback class to target node
    if (isValid) {
      targetNode.className = "drop-target-valid";
    } else {
      targetNode.className = "drop-target-invalid";
    }
  };

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    console.log("drag end", active, over);
    if (!over || !active.data?.current?.current) return;

    const draggedItem = active.data.current.current;
    const dropZoneId = over.id as string;

    const [nodeId, zoneType] = dropZoneId.split("-zone")[0].split("-");

    // Find target node
    const targetNode = nodes.find((node) => node.id === nodeId);
    if (!targetNode) return;

    // Validate drop
    const isValid = validateDropTarget(draggedItem.type, targetNode.data.type);
    if (!isValid) return;

    const position = {
      x: event.delta.x,
      y: event.delta.y,
    };

    console.log("adding ", draggedItem);

    // Pass both new node data AND target node id
    addNode(
      draggedItem.type as ComponentTypes,
      position,
      draggedItem.config,
      nodeId
    );
  };

  const onDragStart = (item: DragItem) => {
    // We can add any drag start logic here if needed
  };
  return (
    <DndContext
      sensors={sensors}
      onDragEnd={handleDragEnd}
      onDragOver={handleDragOver}
    >
      <Layout className=" bg-primary ">
        <Sider width={300} className="bg-primary   z-10  mt-2 mr-2  border-r">
          <ComponentLibrary />
        </Sider>

        <Layout className="bg-primary rounded">
          <div className="p-4 pl-0  ">
            <div className="flex items-center gap-4">
              <Button.Group>
                <Button icon={<Undo2 className="w-4 h-4" />} onClick={undo} />
                <Button icon={<Redo2 className="w-4 h-4" />} onClick={redo} />
                <Button
                  icon={<LayoutIcon className="w-4 h-4" />}
                  onClick={layoutNodes}
                  title="Auto-arrange nodes"
                />
              </Button.Group>

              <Button
                type="primary"
                icon={<Save className="w-4 h-4" />}
                onClick={handleSave}
              >
                Save
              </Button>
            </div>
          </div>

          <Content className=" rounded bg-primary ">
            <ReactFlow
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              //   onNodeClick={(_, node) => setSelectedNode(node.id)}
              style={{ background: "#F7F9FB" }}
              nodeTypes={nodeTypes}
              edgeTypes={edgeTypes}
              onDrop={(event) => event.preventDefault()}
              onDragOver={(event) => event.preventDefault()}
              className="rounded"
              fitView
            >
              {/* ReactFlow components */}
              <Background className="rounded" />
            </ReactFlow>
          </Content>
        </Layout>

        {/* <PropertyEditor node={selectedNode} onUpdate={handleNodeUpdate} /> */}
      </Layout>
    </DndContext>
  );
};
