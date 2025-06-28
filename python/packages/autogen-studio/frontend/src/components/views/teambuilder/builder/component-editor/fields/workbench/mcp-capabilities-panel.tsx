import React, { useState, useCallback, useEffect } from "react";
import {
  Button,
  Card,
  Segmented,
  Alert,
  Spin,
  Empty,
  Typography,
  Space,
  Tag,
  Skeleton,
} from "antd";
import {
  Wrench,
  CheckCircle,
  XCircle,
  Settings,
  FileText,
  Package,
  Info,
} from "lucide-react";
import { McpServerParams } from "../../../../../../types/datamodel";
import { mcpAPI, ServerCapabilities } from "../../../../../mcp/api";
import { McpToolsTab } from "./mcp-tools-tab";
import { McpResourcesTab } from "./mcp-resources-tab";
import { McpPromptsTab } from "./mcp-prompts-tab";

const { Text, Title } = Typography;

interface McpCapabilitiesPanelProps {
  serverParams: McpServerParams;
}

export const McpCapabilitiesPanel: React.FC<McpCapabilitiesPanelProps> = ({
  serverParams,
}) => {
  const [capabilities, setCapabilities] = useState<ServerCapabilities | null>(
    null
  );
  const [loadingCapabilities, setLoadingCapabilities] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>("tools");
  const [hasAttemptedLoad, setHasAttemptedLoad] = useState(false);
  const [loadingContent, setLoadingContent] = useState(false);

  const handleGetCapabilities = useCallback(async () => {
    setLoadingCapabilities(true);
    setError(null);
    setHasAttemptedLoad(true);

    try {
      const result = await mcpAPI.getCapabilities(serverParams);

      if (result.status && result.capabilities) {
        setCapabilities(result.capabilities);

        // Auto-switch to first available capability tab
        if (result.capabilities.tools) {
          setActiveTab("tools");
        } else if (result.capabilities.resources) {
          setActiveTab("resources");
        } else if (result.capabilities.prompts) {
          setActiveTab("prompts");
        }
      } else {
        setError(result.message);
      }
    } catch (err: any) {
      setError(`Failed to fetch capabilities: ${err.message}`);
    } finally {
      setLoadingCapabilities(false);
    }
  }, [serverParams]);

  // Handle tab switching with loading state to minimize jankiness
  const handleTabChange = useCallback((value: string) => {
    setLoadingContent(true);
    setActiveTab(value);

    // Brief delay to show skeleton and allow content to prepare
    setTimeout(() => {
      setLoadingContent(false);
    }, 150);
  }, []);

  // Remove auto-load on mount - user will trigger manually

  const renderInitialState = () => (
    <div style={{ textAlign: "center", padding: "24px 16px" }}>
      <Text
        type="secondary"
        style={{
          display: "block",
          marginBottom: "24px",
          fontSize: "14px",
          lineHeight: "1.5",
        }}
      >
        Connect to discover what tools, resources, and prompts this MCP server
        provides
      </Text>
      <Button
        type="primary"
        onClick={handleGetCapabilities}
        loading={loadingCapabilities}
        icon={<Info size={16} />}
        size="large"
        style={{
          borderRadius: "6px",
          height: "40px",
          padding: "0 24px",
          fontWeight: 500,
        }}
      >
        {loadingCapabilities ? "Connecting..." : "Discover Server Capabilities"}
      </Button>
    </div>
  );

  if (error) {
    return (
      <Alert
        type="error"
        message="Failed to Connect"
        description={
          <div>
            <Text>{error}</Text>
            <div style={{ marginTop: "8px" }}>
              <Text type="secondary" style={{ fontSize: "12px" }}>
                Make sure the MCP server is running and accessible
              </Text>
            </div>
          </div>
        }
        action={
          <Button
            size="small"
            onClick={handleGetCapabilities}
            loading={loadingCapabilities}
            type="primary"
            style={{ borderRadius: "4px" }}
          >
            Try Again
          </Button>
        }
        style={{ marginBottom: "16px" }}
      />
    );
  }

  if (loadingCapabilities) {
    return (
      <div style={{ textAlign: "center", padding: "32px 16px" }}>
        <Spin size="large" style={{ marginBottom: "16px" }} />
        <div>
          <Text strong style={{ display: "block", marginBottom: "4px" }}>
            Connecting to MCP Server
          </Text>
          <Text type="secondary" style={{ fontSize: "13px" }}>
            Discovering available capabilities...
          </Text>
        </div>
      </div>
    );
  }

  // Show initial state if user hasn't attempted to load capabilities yet
  if (!hasAttemptedLoad || !capabilities) {
    return renderInitialState();
  }

  // Create segmented options based on available capabilities
  const segmentedOptions = [];

  if (capabilities?.tools) {
    segmentedOptions.push({
      label: (
        <span
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
          }}
        >
          <Wrench size={16} />
          <span>Tools</span>
        </span>
      ),
      value: "tools",
    });
  }

  if (capabilities?.resources) {
    segmentedOptions.push({
      label: (
        <span
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
          }}
        >
          <Package size={16} />
          <span>Resources</span>
        </span>
      ),
      value: "resources",
    });
  }

  if (capabilities?.prompts) {
    segmentedOptions.push({
      label: (
        <span
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
          }}
        >
          <FileText size={16} />
          <span>Prompts</span>
        </span>
      ),
      value: "prompts",
    });
  }

  // Render the active tab content
  const renderActiveContent = () => {
    switch (activeTab) {
      case "tools":
        return <McpToolsTab serverParams={serverParams} />;
      case "resources":
        return <McpResourcesTab serverParams={serverParams} />;
      case "prompts":
        return <McpPromptsTab serverParams={serverParams} />;
      default:
        return null;
    }
  };

  return (
    <div>
      {/* Only show segmented control if there are actual functional capabilities */}
      {(capabilities?.tools ||
        capabilities?.resources ||
        capabilities?.prompts) && (
        <div>
          <Segmented
            value={activeTab}
            onChange={setActiveTab}
            options={segmentedOptions}
            style={{ marginBottom: "16px" }}
          />
          <div>{renderActiveContent()}</div>
        </div>
      )}
    </div>
  );
};
