import React from "react";
import { Card, Button, Alert, Badge, Descriptions } from "antd";
import {
  Server,
  Play,
  Settings,
  CheckCircle,
  XCircle,
  Info,
} from "lucide-react";
import type { Component, McpWorkbenchConfig } from "../../types/datamodel";
import WorkbenchFields from "../teambuilder/builder/component-editor/fields/workbench-fields";

interface McpDetailProps {
  workbench: Component<McpWorkbenchConfig>;
  onTestConnection: () => void;
}

const McpDetail: React.FC<McpDetailProps> = ({
  workbench,
  onTestConnection,
}) => {
  const serverParams = workbench.config.server_params;
  const serverType =
    serverParams?.type?.replace("ServerParams", "") || "Unknown";

  return (
    <div className="h-full space-y-6">
      <WorkbenchFields
        component={workbench}
        defaultPanelKey={["testing"]}
        onChange={() => {
          // In the playground, we don't allow editing - this is read-only
          // The user would need to go to the Team Builder to make changes
        }}
      />
    </div>
  );
};

export default McpDetail;
