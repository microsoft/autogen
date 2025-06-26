import React, { useState, useCallback, useEffect } from "react";
import {
  Button,
  Card,
  Tabs,
  Alert,
  Spin,
  Empty,
  Typography,
  Space,
  Tag,
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
const { TabPane } = Tabs;

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

  // Remove auto-load on mount - user will trigger manually

  const renderInitialState = () => (
    <div style={{ textAlign: "center", padding: "24px 16px" }}>
      <Title level={4} style={{ margin: "0 0 8px 0", color: "#262626" }}>
        MCP Server Capabilities
      </Title>
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

  const renderCapabilitiesOverview = () => {
    if (!capabilities) return null;

    const capabilityItems = [];

    if (capabilities.tools) {
      capabilityItems.push({
        key: "tools",
        icon: <Wrench size={12} />,
        label: "Tools",
        color: "blue",
        extra: capabilities.tools.listChanged ? "Live Updates" : null,
      });
    }

    if (capabilities.resources) {
      const features = [];
      if (capabilities.resources.subscribe) features.push("Subscribe");
      if (capabilities.resources.listChanged) features.push("Live Updates");

      capabilityItems.push({
        key: "resources",
        icon: <Package size={12} />,
        label: "Resources",
        color: "green",
        extra: features.length > 0 ? features.join(", ") : null,
      });
    }

    if (capabilities.prompts) {
      capabilityItems.push({
        key: "prompts",
        icon: <FileText size={12} />,
        label: "Prompts",
        color: "purple",
        extra: capabilities.prompts.listChanged ? "Live Updates" : null,
      });
    }

    if (capabilities.logging) {
      capabilityItems.push({
        key: "logging",
        icon: <Settings size={12} />,
        label: "Logging",
        color: "orange",
        extra: null,
      });
    }

    if (capabilities.sampling) {
      capabilityItems.push({
        key: "sampling",
        icon: <Settings size={12} />,
        label: "Sampling",
        color: "cyan",
        extra: null,
      });
    }

    return (
      <div
        style={{
          display: "flex",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            flex: 1,
          }}
        >
          <Info size={14} style={{ color: "#1890ff", flexShrink: 0 }} />
          <Text style={{ fontSize: "14px", flexShrink: 0 }}>
            This server supports:
          </Text>

          <div
            style={{ display: "flex", flexWrap: "wrap", gap: "6px", flex: 1 }}
          >
            {capabilityItems.length > 0 ? (
              capabilityItems.map((item) => (
                <div
                  key={item.key}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    padding: "3px 8px",
                    borderRadius: "12px",
                    backgroundColor:
                      item.color === "blue"
                        ? "#e6f7ff"
                        : item.color === "green"
                        ? "#f6ffed"
                        : item.color === "purple"
                        ? "#f9f0ff"
                        : item.color === "orange"
                        ? "#fff7e6"
                        : item.color === "cyan"
                        ? "#e6fffb"
                        : "#f0f0f0",
                    border: `1px solid ${
                      item.color === "blue"
                        ? "#91d5ff"
                        : item.color === "green"
                        ? "#b7eb8f"
                        : item.color === "purple"
                        ? "#d3adf7"
                        : item.color === "orange"
                        ? "#ffd591"
                        : item.color === "cyan"
                        ? "#87e8de"
                        : "#d9d9d9"
                    }`,
                    gap: "4px",
                  }}
                >
                  <span
                    style={{
                      color:
                        item.color === "blue"
                          ? "#1890ff"
                          : item.color === "green"
                          ? "#52c41a"
                          : item.color === "purple"
                          ? "#722ed1"
                          : item.color === "orange"
                          ? "#fa8c16"
                          : item.color === "cyan"
                          ? "#13c2c2"
                          : "#595959",
                    }}
                  >
                    {item.icon}
                  </span>
                  <Text
                    style={{
                      fontSize: "12px",
                      fontWeight: 500,
                      color:
                        item.color === "blue"
                          ? "#1890ff"
                          : item.color === "green"
                          ? "#52c41a"
                          : item.color === "purple"
                          ? "#722ed1"
                          : item.color === "orange"
                          ? "#fa8c16"
                          : item.color === "cyan"
                          ? "#13c2c2"
                          : "#595959",
                    }}
                  >
                    {item.label}
                  </Text>
                  {item.extra && (
                    <Text
                      type="secondary"
                      style={{
                        fontSize: "10px",
                        fontStyle: "italic",
                      }}
                    >
                      ({item.extra})
                    </Text>
                  )}
                </div>
              ))
            ) : (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  padding: "3px 8px",
                  borderRadius: "12px",
                  backgroundColor: "#f0f0f0",
                  border: "1px solid #d9d9d9",
                  gap: "4px",
                }}
              >
                <Text type="secondary" style={{ fontSize: "12px" }}>
                  No major capabilities detected
                </Text>
              </div>
            )}
          </div>
        </div>

        <Button
          type="link"
          size="small"
          onClick={handleGetCapabilities}
          loading={loadingCapabilities}
          icon={<Settings size={12} />}
          style={{
            padding: "0 8px",
            height: "auto",
            fontSize: "12px",
            flexShrink: 0,
          }}
        >
          Refresh
        </Button>
      </div>
    );
  };

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

  return (
    <Space direction="vertical" style={{ width: "100%" }} size="large">
      {/* Always show capabilities overview at the top */}
      {renderCapabilitiesOverview()}

      {/* Only show tabs if there are actual functional capabilities */}
      {(capabilities?.tools ||
        capabilities?.resources ||
        capabilities?.prompts) && (
        <Card size="small">
          <Tabs
            activeKey={activeTab}
            onChange={setActiveTab}
            items={[
              ...(capabilities?.tools
                ? [
                    {
                      key: "tools",
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
                      children: <McpToolsTab serverParams={serverParams} />,
                    },
                  ]
                : []),
              ...(capabilities?.resources
                ? [
                    {
                      key: "resources",
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
                      children: <McpResourcesTab serverParams={serverParams} />,
                    },
                  ]
                : []),
              ...(capabilities?.prompts
                ? [
                    {
                      key: "prompts",
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
                      children: <McpPromptsTab serverParams={serverParams} />,
                    },
                  ]
                : []),
            ]}
          />
        </Card>
      )}
    </Space>
  );
};
