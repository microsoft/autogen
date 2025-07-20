import React, { useState } from "react";
import {
  Save,
  Play,
  Square,
  Layout,
  Map,
  Grid,
  MoreHorizontal,
} from "lucide-react";
import { Button, Tooltip, Segmented, Popover, Badge } from "antd";
import { WorkflowStatus } from "./types";

interface ToolbarProps {
  isDirty: boolean;
  onSave: () => void;
  onRun: () => void;
  onStop?: () => void;
  onAutoLayout: () => void;
  onToggleMiniMap: () => void;
  onToggleGrid: () => void;
  showMiniMap: boolean;
  showGrid: boolean;
  disabled: boolean;
  edgeType: string;
  onEdgeTypeChange: (type: string) => void;
  workflowStatus?: WorkflowStatus;
  isConnected?: boolean;
}

export const Toolbar: React.FC<ToolbarProps> = ({
  isDirty,
  onSave,
  onRun,
  onStop,
  onAutoLayout,
  onToggleMiniMap,
  onToggleGrid,
  showMiniMap,
  showGrid,
  disabled,
  edgeType,
  onEdgeTypeChange,
  workflowStatus,
  isConnected,
}) => {
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Advanced settings content
  const advancedContent = (
    <div className="flex flex-col gap-2 w-64">
      <div className="font-semibold text-sm mb-2">View Options</div>

      <div className="flex items-center justify-between">
        <span className="text-sm">Minimap</span>
        <Button
          type={showMiniMap ? "primary" : "default"}
          size="small"
          icon={<Map size={14} />}
          onClick={onToggleMiniMap}
        >
          {showMiniMap ? "Hide" : "Show"}
        </Button>
      </div>

      <div className="flex items-center justify-between">
        <span className="text-sm">Grid</span>
        <Button
          type={showGrid ? "primary" : "default"}
          size="small"
          icon={<Grid size={14} />}
          onClick={onToggleGrid}
        >
          {showGrid ? "Hide" : "Show"}
        </Button>
      </div>

      <div className="border-t pt-2 mt-2">
        <div className="font-semibold text-sm mb-2">Edge Style</div>
        <Segmented
          options={[
            { label: "Smooth", value: "smoothstep" },
            { label: "Straight", value: "straight" },
          ]}
          value={edgeType}
          onChange={(value) => onEdgeTypeChange(value as string)}
          size="small"
        />
      </div>

      <div className="border-t pt-2 mt-2">
        <div className="font-semibold text-sm mb-2">Layout</div>
        <Button
          icon={<Layout size={14} />}
          onClick={onAutoLayout}
          disabled={disabled}
          size="small"
          block
        >
          Auto-arrange Nodes
        </Button>
      </div>
    </div>
  );

  return (
    <div className="absolute top-4 right-4 z-10">
      {/* Main Toolbar - Vertical Layout */}
      <div className="flex flex-col gap-2">
        {/* Primary Actions */}
        <div className="flex flex-col bg-primary rounded-md border p-2 gap-2 border-secondary shadow-sm overflow-hidden">
          {workflowStatus === WorkflowStatus.RUNNING ? (
            <Tooltip title="Stop Workflow" placement="left">
              <Badge
                dot={isConnected}
                status={isConnected ? "processing" : "error"}
              >
                <Button
                  type="primary"
                  danger
                  icon={<Square size={18} />}
                  onClick={onStop}
                  className="h-10 w-10 flex items-center justify-center"
                />
              </Badge>
            </Tooltip>
          ) : (
            <Tooltip title="Run Workflow" placement="left">
              <Badge
                dot={workflowStatus === WorkflowStatus.COMPLETED}
                status="success"
              >
                <Button
                  type="text"
                  icon={<Play size={18} />}
                  onClick={onRun}
                  disabled={disabled}
                  className="h-10 w-10 flex items-center justify-center"
                />
              </Badge>
            </Tooltip>
          )}

          <Tooltip title="Save Workflow" placement="left">
            <Button
              type={isDirty ? "primary" : "text"}
              icon={<Save size={18} />}
              onClick={onSave}
              disabled={!isDirty}
              className="h-10 w-10 flex items-center justify-center"
            />
          </Tooltip>

          <Popover
            content={advancedContent}
            title="Workflow Settings"
            trigger="hover"
            placement="leftTop"
            open={showAdvanced}
            onOpenChange={setShowAdvanced}
          >
            <Button
              type={showAdvanced ? "primary" : "text"}
              icon={<MoreHorizontal size={18} />}
              className="h-10 w-10 flex items-center justify-center"
            />
          </Popover>
        </div>
      </div>
    </div>
  );
};

export default Toolbar;
