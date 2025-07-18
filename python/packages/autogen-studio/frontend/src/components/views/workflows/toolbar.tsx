import React, { useState } from "react";
import {
  Save,
  Play,
  Layout,
  Map,
  Grid,
  MoreVertical,
  Settings,
} from "lucide-react";
import { Button, Tooltip, Segmented, Popover } from "antd";

interface ToolbarProps {
  isDirty: boolean;
  onSave: () => void;
  onRun: () => void;
  onAutoLayout: () => void;
  onToggleMiniMap: () => void;
  onToggleGrid: () => void;
  showMiniMap: boolean;
  showGrid: boolean;
  disabled: boolean;
  edgeType: string;
  onEdgeTypeChange: (type: string) => void;
}

export const Toolbar: React.FC<ToolbarProps> = ({
  isDirty,
  onSave,
  onRun,
  onAutoLayout,
  onToggleMiniMap,
  onToggleGrid,
  showMiniMap,
  showGrid,
  disabled,
  edgeType,
  onEdgeTypeChange,
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
            { label: "Step", value: "step" },
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
        <div className="flex flex-col bg-primary rounded-md border border-secondary shadow-sm overflow-hidden">
          <Tooltip title="Run Workflow" placement="left">
            <Button
              type="text"
              icon={<Play size={18} />}
              onClick={onRun}
              disabled={disabled}
              className="h-10 w-10 flex items-center justify-center"
            />
          </Tooltip>

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
            trigger="click"
            placement="leftTop"
            open={showAdvanced}
            onOpenChange={setShowAdvanced}
          >
            <Tooltip title="More Options" placement="left">
              <Button
                type={showAdvanced ? "primary" : "text"}
                icon={<Settings size={18} />}
                className="h-10 w-10 flex items-center justify-center"
              />
            </Tooltip>
          </Popover>
        </div>
      </div>
    </div>
  );
};

export default Toolbar;
