import { Node, Edge } from "@xyflow/react";
import {
  TeamConfig,
  ComponentConfigTypes,
  ComponentTypes,
} from "../../../../types/datamodel";

interface NodeConnections {
  modelClient: string | null;
  tools: string[];
  participants: string[];
  termination: string | null;
}

export interface NodeData extends Record<string, unknown> {
  label: string;
  type: ComponentTypes;
  config: ComponentConfigTypes;
  connections: NodeConnections;
}

// Define our node type that extends the XYFlow Node type
export type CustomNode = Node<NodeData>;
// export type CustomEdge = Edge;

export type EdgeTypes =
  | "model-connection"
  | "tool-connection"
  | "agent-connection"
  | "team-connection"
  | "termination-connection";

export interface CustomEdge extends Edge {
  type: EdgeTypes;
}

export interface Position {
  x: number;
  y: number;
}
export interface GraphState {
  nodes: CustomNode[];
  edges: CustomEdge[];
}

export interface TeamBuilderState {
  nodes: CustomNode[];
  edges: CustomEdge[];
  selectedNodeId: string | null;
  history: Array<{ nodes: CustomNode[]; edges: CustomEdge[] }>;
  currentHistoryIndex: number;
  originalConfig: TeamConfig | null;
  addNode: (
    type: ComponentTypes,
    position: Position,
    config: ComponentConfigTypes,
    targetNodeId?: string
  ) => void;

  updateNode: (nodeId: string, updates: Partial<NodeData>) => void;
  removeNode: (nodeId: string) => void;

  addEdge: (edge: CustomEdge) => void;
  removeEdge: (edgeId: string) => void;

  setSelectedNode: (nodeId: string | null) => void;

  undo: () => void;
  redo: () => void;

  // Sync with JSON
  syncToJson: () => TeamConfig | null;
  loadFromJson: (config: TeamConfig) => GraphState;
  layoutNodes: () => void;
}

export interface FormFieldMapping {
  fieldName: string;
  type: "input" | "textarea" | "select" | "number" | "switch";
  label: string;
  required?: boolean;
  options?: { label: string; value: any }[];
  validate?: (value: any) => boolean;
}

export interface DragItem {
  type: ComponentTypes;
  config: ComponentConfigTypes;
}

export interface NodeComponentProps {
  data: NodeData;
  selected: boolean;
  onClick: () => void;
}

export interface PropertyEditorProps {
  node: CustomNode | null;
  onUpdate: (updates: Partial<NodeData>) => void;
}

export interface LibraryProps {
  onDragStart: (item: DragItem) => void;
}

export interface VisualizerProps {
  nodes: CustomNode[];
  edges: CustomEdge[];
  onNodesChange: (changes: any[]) => void;
  onEdgesChange: (changes: any[]) => void;
  onNodeClick: (nodeId: string) => void;
  onConnect: (params: any) => void;
}
