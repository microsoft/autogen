import React from "react";
import { Button, Tooltip, Dropdown } from "antd";
import type { MenuProps } from "antd";
import {
  Maximize2,
  Minimize2,
  ArrowDown,
  ArrowRight,
  MessageSquareIcon,
  MessageSquareOffIcon,
  MoreHorizontal,
  Grid,
  Hash,
  MessageSquare,
  LayoutGrid,
  RotateCcw,
  MapIcon,
} from "lucide-react";
import { useConfigStore } from "../../../../../hooks/store";

interface AgentFlowToolbarProps {
  isFullscreen: boolean;
  onToggleFullscreen: () => void;
  onResetView?: () => void;
}

export const AgentFlowToolbar: React.FC<AgentFlowToolbarProps> = ({
  isFullscreen,
  onToggleFullscreen,
  onResetView,
}) => {
  const { agentFlow: settings, setAgentFlowSettings } = useConfigStore();

  const toggleSetting = (setting: keyof typeof settings) => () => {
    setAgentFlowSettings({
      [setting]: !settings[setting],
    });
  };

  const menuItems: MenuProps["items"] = [
    {
      key: "grid",
      label: "Show Grid",
      icon: <Grid size={16} />,
      onClick: toggleSetting("showGrid"),
    },
    {
      key: "tokens",
      label: "Show Tokens",
      icon: <Hash size={16} />,
      onClick: toggleSetting("showTokens"),
    },
    // {
    //   key: "messages",
    //   label: "Show Messages",
    //   icon: <MessageSquare size={16} />,
    //   onClick: toggleSetting("showMessages"),
    // },
    {
      key: "miniMap",
      label: "Mini Map",
      icon: <MapIcon size={16} />,
      onClick: toggleSetting("showMiniMap"),
    },
    {
      type: "divider",
    },
    {
      key: "reset",
      label: "Reset View",
      icon: <RotateCcw size={16} />,
      onClick: onResetView,
      disabled: !onResetView,
    },
  ];

  return (
    <div className="absolute top-2 right-2 bg-secondary bg-opacity-70 hover:bg-secondary rounded backdrop-blur-sm z-50">
      <div className="p-1 flex items-center gap-1">
        <Tooltip title={isFullscreen ? "Exit Fullscreen" : "Enter Fullscreen"}>
          <Button
            type="text"
            icon={
              isFullscreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />
            }
            className="p-1.5 hover:bg-primary/10 rounded-md text-primary/75 hover:text-primary"
            onClick={onToggleFullscreen}
          />
        </Tooltip>

        <Tooltip
          title={`Switch to ${
            settings.direction === "TB" ? "Horizontal" : "Vertical"
          } Layout`}
        >
          <Button
            type="text"
            icon={
              settings.direction === "TB" ? (
                <ArrowDown size={18} />
              ) : (
                <ArrowRight size={18} />
              )
            }
            className="p-1.5 hover:bg-primary/10 rounded-md text-primary/75 hover:text-primary"
            onClick={() =>
              setAgentFlowSettings({
                direction: settings.direction === "TB" ? "LR" : "TB",
              })
            }
          />
        </Tooltip>

        <Tooltip title={settings.showLabels ? "Hide Labels" : "Show Labels"}>
          <Button
            type="text"
            icon={
              settings.showLabels ? (
                <MessageSquareIcon size={18} />
              ) : (
                <MessageSquareOffIcon size={18} />
              )
            }
            className="p-1.5 hover:bg-primary/10 rounded-md text-primary/75 hover:text-primary"
            onClick={toggleSetting("showLabels")}
          />
        </Tooltip>

        <Dropdown
          menu={{ items: menuItems }}
          trigger={["click"]}
          getPopupContainer={(triggerNode) =>
            triggerNode.parentNode as HTMLElement
          }
          overlayStyle={{ zIndex: 1000 }}
        >
          <Button
            type="text"
            icon={<MoreHorizontal size={18} />}
            className="p-1.5 hover:bg-primary/10 rounded-md text-primary/75 hover:text-primary"
            title="More Options" // Use native title instead of Tooltip
          />
        </Dropdown>
      </div>
    </div>
  );
};
