import React, { useState, useCallback, useRef } from "react";
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
  Wifi,
  WifiOff,
  Play,
  Unplug,
} from "lucide-react";
import { McpServerParams } from "../../../../../../types/datamodel";
import {
  ServerCapabilities,
  McpWebSocketState,
  McpWebSocketClient,
} from "../../../../../mcp/api";
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
  const [wsState, setWsState] = useState<McpWebSocketState>({
    connected: false,
    connecting: false,
    capabilities: null,
    sessionId: null,
    error: null,
    lastActivity: null,
  });
  const [wsClient, setWsClient] = useState<McpWebSocketClient | null>(null);
  const [activeTab, setActiveTab] = useState<string>("tools");
  const [loadingContent, setLoadingContent] = useState(false);
  const wsClientRef = useRef<McpWebSocketClient | null>(null);

  const { connected, connecting, capabilities, error } = wsState;

  // Keep ref in sync with state
  React.useEffect(() => {
    wsClientRef.current = wsClient;
  }, [wsClient]);

  // Handle manual connection
  const handleConnect = useCallback(async () => {
    // Disconnect any existing client (should already be done by useEffect, but just in case)
    if (wsClient) {
      wsClient.disconnect();
    }

    const client = new McpWebSocketClient(serverParams, (stateUpdate) => {
      setWsState((prev) => {
        const newState = { ...prev, ...stateUpdate };
        return newState;
      });
    });

    setWsClient(client);
    await client.connect();
  }, [serverParams]);

  // Handle disconnect
  const handleDisconnect = useCallback(() => {
    if (wsClient) {
      wsClient.disconnect();
      setWsClient(null);
    }
  }, [wsClient]);

  // Handle tab switching with loading state to minimize jankiness
  const handleTabChange = useCallback((value: string) => {
    setLoadingContent(true);
    setActiveTab(value);

    // Brief delay to show skeleton and allow content to prepare
    setTimeout(() => {
      setLoadingContent(false);
    }, 150);
  }, []);

  // Reset connection and state when server parameters change
  React.useEffect(() => {
    // Disconnect current connection if it exists
    const currentClient = wsClientRef.current;
    if (currentClient) {
      currentClient.disconnect();
      setWsClient(null);
    }

    // Reset all state to initial values
    setWsState({
      connected: false,
      connecting: false,
      capabilities: null,
      sessionId: null,
      error: null,
      lastActivity: null,
    });

    // Reset UI state
    setActiveTab("tools");
    setLoadingContent(false);
  }, [serverParams]); // Only depends on serverParams

  // Auto-switch to first available capability tab when capabilities are loaded
  React.useEffect(() => {
    if (capabilities) {
      if (capabilities.tools) {
        setActiveTab("tools");
      } else if (capabilities.resources) {
        setActiveTab("resources");
      } else if (capabilities.prompts) {
        setActiveTab("prompts");
      }
    }
  }, [capabilities]);

  // Cleanup effect - disconnect when component unmounts
  React.useEffect(() => {
    return () => {
      if (wsClient) {
        wsClient.disconnect();
      }
    };
  }, [wsClient]);

  const renderConnectionStatus = () => {
    if (connecting) {
      return (
        <div className="text-center py-8 px-4">
          <Spin size="large" className="mb-4" />
          <div>
            <Text strong className="block mb-2">
              Connecting to MCP Server
            </Text>
            <Text type="secondary" className="text-sm">
              Establishing WebSocket connection and discovering capabilities...
            </Text>
          </div>
          <div className="mt-4">
            <Button
              onClick={handleDisconnect}
              size="small"
              icon={<Unplug size={14} />}
            >
              Cancel
            </Button>
          </div>
        </div>
      );
    }

    if (error) {
      return (
        <Alert
          message="Connection Error"
          description={
            <div>
              <Text>{error}</Text>
              {error.includes("JSON") && (
                <div className="mt-2">
                  <Text type="secondary" className="text-xs">
                    This might indicate the AutoGen Studio server is not running
                    or the MCP routes are not properly configured.
                  </Text>
                </div>
              )}
              <div className="mt-3">
                <Space>
                  <Button
                    type="primary"
                    size="small"
                    onClick={handleConnect}
                    icon={<Wifi size={14} />}
                  >
                    Retry Connection
                  </Button>
                  <Button
                    size="small"
                    onClick={handleDisconnect}
                    icon={<Unplug size={14} />}
                  >
                    Reset
                  </Button>
                </Space>
              </div>
            </div>
          }
          type="error"
          showIcon
          className="m-4"
        />
      );
    }

    if (!connected && !capabilities) {
      return (
        <div className="text-center py-8 px-4">
          <div className="mb-6">
            <Title level={4} className="mb-2 text-secondary">
              MCP Server Testing Panel
            </Title>
            <Text
              type="secondary"
              className="block text-sm leading-relaxed max-w-md mx-auto"
            >
              Click the button below to establish a WebSocket connection and
              discover what tools, resources, and prompts are available from
              this MCP server.
            </Text>
          </div>
          <Button
            type="primary"
            onClick={handleConnect}
            icon={<Play size={16} />}
            size="large"
            className="rounded-md h-10 px-6 font-medium"
          >
            Connect to Server
          </Button>
          <div className="mt-4">
            <Text type="secondary" className="text-xs">
              Server: {serverParams.type} •{" "}
              {(serverParams as any).command ||
                (serverParams as any).url ||
                "Unknown"}
            </Text>
          </div>
        </div>
      );
    }

    return null;
  };

  const renderConnectionIndicator = () => {
    if (!connected && !connecting) {
      return (
        <Tag
          color="red"
          icon={<WifiOff className="inline-block mr-1" size={12} />}
        >
          Disconnected
        </Tag>
      );
    }

    if (connecting) {
      return (
        <Tag color="orange" icon={<Spin size="small" />}>
          Connecting
        </Tag>
      );
    }

    return (
      <Tag
        color="green"
        icon={<Wifi className="inline-block mr-1" size={12} />}
      >
        Connected
      </Tag>
    );
  };

  // Show connection status if not connected or no capabilities
  const connectionStatus = renderConnectionStatus();
  if (connectionStatus) {
    return connectionStatus;
  }

  // Create segmented options based on available capabilities
  const segmentedOptions = [];

  if (capabilities?.tools) {
    segmentedOptions.push({
      label: (
        <span className="flex items-center gap-1.5">
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
        <span className="flex items-center gap-1.5">
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
        <span className="flex items-center gap-1.5">
          <FileText size={16} />
          <span>Prompts</span>
        </span>
      ),
      value: "prompts",
    });
  }

  // Render the active tab content
  const renderActiveContent = () => {
    if (loadingContent) {
      return (
        <div className="p-6">
          <Skeleton active paragraph={{ rows: 4 }} />
        </div>
      );
    }

    switch (activeTab) {
      case "tools":
        return (
          <McpToolsTab
            serverParams={serverParams}
            wsClient={wsClient}
            connected={connected}
            capabilities={capabilities}
          />
        );
      case "resources":
        return (
          <McpResourcesTab
            serverParams={serverParams}
            wsClient={wsClient}
            connected={connected}
            capabilities={capabilities}
          />
        );
      case "prompts":
        return (
          <McpPromptsTab
            serverParams={serverParams}
            wsClient={wsClient}
            connected={connected}
            capabilities={capabilities}
          />
        );
      default:
        return (
          <Empty
            description="Select a capability to explore"
            className="py-12 px-6"
          />
        );
    }
  };

  return (
    <div className="h-full flex flex-col">
      <div>
        <div className="flex justify-between items-center mb-3">
          <Title level={5} className="m-0">
            Server Capabilities
          </Title>
          <Space>
            {renderConnectionIndicator()}
            {connected && (
              <Button
                size="small"
                onClick={handleDisconnect}
                icon={<Unplug size={12} />}
                type="text"
              >
                Disconnect
              </Button>
            )}
          </Space>
        </div>

        {segmentedOptions.length > 0 && (
          <Segmented
            options={segmentedOptions}
            value={activeTab}
            onChange={handleTabChange}
            className="w-full"
          />
        )}
      </div>

      <div className="flex-1 overflow-hidden">
        {connected && !capabilities && !error ? (
          // Show loading state when connected but capabilities not yet received
          <div className="text-center py-12 px-6">
            <Spin size="large" className="mb-4" />
            <div>
              <Text strong className="block mb-2">
                Discovering Server Capabilities
              </Text>
              <Text type="secondary" className="text-sm">
                Retrieving available tools, resources, and prompts...
              </Text>
            </div>
          </div>
        ) : segmentedOptions.length === 0 ? (
          <Empty
            description={
              <div className="text-center">
                <Text type="secondary">
                  This MCP server doesn't expose any capabilities
                </Text>
                <br />
                <Text type="secondary" className="text-xs">
                  No tools, resources, or prompts are available
                </Text>
              </div>
            }
            className="py-12 px-6"
          />
        ) : (
          renderActiveContent()
        )}
      </div>
    </div>
  );
};
