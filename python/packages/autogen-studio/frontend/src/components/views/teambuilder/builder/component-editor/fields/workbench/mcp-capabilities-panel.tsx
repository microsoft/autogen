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
  Collapse,
  Badge,
  Tooltip,
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
  Activity,
  ChevronDown,
  ChevronUp,
  MessageSquare,
} from "lucide-react";
import { McpServerParams } from "../../../../../../types/datamodel";
import {
  ServerCapabilities,
  McpWebSocketState,
  McpWebSocketClient,
  McpActivityMessage,
  ElicitationRequest,
  ElicitationResponse,
} from "../../../../../../views/mcp/api";
import { McpToolsTab } from "./mcp-tools-tab";
import { McpResourcesTab } from "./mcp-resources-tab";
import { McpPromptsTab } from "./mcp-prompts-tab";
import { ElicitationDialog, ElicitationBadge } from "./elicitation-dialog";

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
    activityMessages: [],
    pendingElicitations: [],
  });
  const [wsClient, setWsClient] = useState<McpWebSocketClient | null>(null);
  const [activeTab, setActiveTab] = useState<string>("tools");
  const [loadingContent, setLoadingContent] = useState(false);
  const wsClientRef = useRef<McpWebSocketClient | null>(null);

  // Activity stream state
  const [activityExpanded, setActivityExpanded] = useState<string[]>([]);
  const activityStreamRef = useRef<HTMLDivElement>(null);

  // Elicitation state
  const [currentElicitation, setCurrentElicitation] =
    useState<ElicitationRequest | null>(null);
  const [elicitationDialogVisible, setElicitationDialogVisible] =
    useState(false);

  const { connected, connecting, capabilities, error, pendingElicitations } =
    wsState;

  // Auto-scroll to bottom when new messages arrive
  React.useEffect(() => {
    if (activityStreamRef.current && wsState.activityMessages.length > 0) {
      activityStreamRef.current.scrollTo({
        top: activityStreamRef.current.scrollHeight,
        behavior: "smooth",
      });
    }
  }, [wsState.activityMessages]);

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

    const client = new McpWebSocketClient(
      serverParams,
      (stateUpdate: Partial<McpWebSocketState>) => {
        setWsState((prev: McpWebSocketState) => {
          const newState = { ...prev, ...stateUpdate };
          return newState;
        });
      }
    );

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
      activityMessages: [],
      pendingElicitations: [],
    });

    // Reset UI state
    setActiveTab("tools");
    setLoadingContent(false);
    setCurrentElicitation(null);
    setElicitationDialogVisible(false);
    setActivityExpanded([]);
  }, [serverParams]); // Only depends on serverParams

  // Handle elicitation requests - show dialog for the first pending elicitation
  React.useEffect(() => {
    if (pendingElicitations.length > 0 && !currentElicitation) {
      const firstElicitation = pendingElicitations[0];
      setCurrentElicitation(firstElicitation);
      setElicitationDialogVisible(true);
    } else if (pendingElicitations.length === 0 && currentElicitation) {
      // No more pending elicitations, close dialog
      setCurrentElicitation(null);
      setElicitationDialogVisible(false);
    }
  }, [pendingElicitations, currentElicitation]);

  // Handle elicitation response
  const handleElicitationResponse = useCallback(
    (response: ElicitationResponse) => {
      if (wsClient && currentElicitation) {
        wsClient.sendElicitationResponse(response);

        // Clear current elicitation and close dialog
        setCurrentElicitation(null);
        setElicitationDialogVisible(false);

        // If there are more pending elicitations, show the next one
        if (pendingElicitations.length > 1) {
          // This will be handled by the useEffect that watches pendingElicitations
        }
      } else {
        console.error(
          "McpCapabilitiesPanel: Cannot send response - missing wsClient or currentElicitation"
        );
      }
    },
    [wsClient, currentElicitation, pendingElicitations]
  );

  // Handle elicitation dialog close (cancel)
  const handleElicitationCancel = useCallback(() => {
    if (currentElicitation) {
      // Send a cancel response
      const cancelResponse: ElicitationResponse = {
        type: "elicitation_response",
        request_id: currentElicitation.request_id,
        action: "cancel",
        session_id: currentElicitation.session_id,
      };
      handleElicitationResponse(cancelResponse);
    }
  }, [currentElicitation, handleElicitationResponse]);

  // Cleanup effect - disconnect when component unmounts
  React.useEffect(() => {
    return () => {
      console.log("Component unmounting, disconnecting WebSocket");
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
            key="tools-tab"
            serverParams={serverParams}
            wsClient={wsClient}
            connected={connected}
            capabilities={capabilities}
          />
        );
      case "resources":
        return (
          <McpResourcesTab
            key="resources-tab"
            serverParams={serverParams}
            wsClient={wsClient}
            connected={connected}
            capabilities={capabilities}
          />
        );
      case "prompts":
        return (
          <McpPromptsTab
            key="prompts-tab"
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

  const renderActivityStream = () => {
    const { activityMessages } = wsState;

    if (!connected || activityMessages.length === 0) {
      return null;
    }

    return (
      <div className="h-full flex flex-col border-l border-gray-200">
        {/* Header */}
        <div className="px-4 py-3 border-b border-gray-200  ">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity size={16} className="text-gray-600" />
              <span className="font-medium text-sm">Notification Stream</span>
              <Badge count={activityMessages.length} size="small" />
            </div>
            <Button
              size="small"
              type="text"
              onClick={() =>
                setWsState((prev) => ({ ...prev, activityMessages: [] }))
              }
              className="text-xs"
            >
              Clear
            </Button>
          </div>
        </div>

        {/* Messages Container */}
        <div
          ref={activityStreamRef}
          className="flex-1 overflow-y-auto p-2 space-y-1"
        >
          {activityMessages.map((msg: McpActivityMessage) => (
            <div
              key={msg.id}
              className="border bg-secondary rounded p-2 hover:bg-primary transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <span className="text-gray-500 flex-shrink-0">
                    {msg.activity_type === "protocol" && <Activity size={14} />}
                    {msg.activity_type === "error" && <XCircle size={14} />}
                    {msg.activity_type === "sampling" && (
                      <CheckCircle size={14} />
                    )}
                    {msg.activity_type === "elicitation" && (
                      <MessageSquare size={14} />
                    )}
                  </span>
                  <Text className="text-sm truncate flex-1">{msg.message}</Text>
                </div>
                <Text
                  type="secondary"
                  className="text-xs whitespace-nowrap ml-2 flex-shrink-0"
                >
                  {msg.timestamp.toLocaleTimeString()}
                </Text>
              </div>
              {msg.details && (
                <Collapse
                  ghost
                  size="small"
                  className="mt-1"
                  items={[
                    {
                      key: "1",
                      label: (
                        <Text type="secondary" className="text-xs">
                          View Details
                        </Text>
                      ),
                      children: (
                        <pre className="bg-gray-50 p-2 rounded text-xs overflow-x-auto mt-1">
                          {JSON.stringify(msg.details, null, 2)}
                        </pre>
                      ),
                    },
                  ]}
                />
              )}
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col">
      <div>
        <div className="flex justify-between items-center mb-3">
          <div className="flex items-center gap-2">
            <Title level={5} className="m-0">
              Server Capabilities
            </Title>
            {pendingElicitations.length > 0 && (
              <ElicitationBadge count={pendingElicitations.length} />
            )}
          </div>
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

      {/* Main content area with stable layout to prevent component remounting */}
      <div className="flex-1 overflow-hidden mt-3">
        {/* Always use the same container structure to prevent React from unmounting components */}
        <div
          className="h-full grid gap-4"
          style={{
            gridTemplateColumns:
              connected && wsState.activityMessages.length > 0
                ? "1fr 400px"
                : "1fr",
          }}
        >
          {/* Main content panel */}
          <div className="h-full overflow-auto">
            {connected && !capabilities && !error ? (
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

          {/* Activity stream panel - only rendered when there are messages */}
          {connected &&
            wsState.activityMessages.length > 0 &&
            renderActivityStream()}
        </div>
      </div>

      {/* Elicitation Dialog - add this outside the main flex container */}
      {currentElicitation && (
        <ElicitationDialog
          visible={elicitationDialogVisible}
          onCancel={handleElicitationCancel}
          request={currentElicitation}
          onResponse={handleElicitationResponse}
        />
      )}
    </div>
  );
};
