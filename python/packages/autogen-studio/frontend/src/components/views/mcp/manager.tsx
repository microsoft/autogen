import React, { useCallback, useEffect, useState, useContext } from "react";
import { message } from "antd";
import { ChevronRight } from "lucide-react";
import { appContext } from "../../../hooks/provider";
import McpSidebar from "./sidebar";
import McpDetail from "./detail";
import { mcpAPI } from "./api";
import type {
  Gallery,
  Component,
  McpWorkbenchConfig,
} from "../../types/datamodel";

const McpManager: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [currentWorkbench, setCurrentWorkbench] =
    useState<Component<McpWorkbenchConfig> | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(() => {
    if (typeof window !== "undefined") {
      const stored = localStorage.getItem("mcpSidebar");
      return stored !== null ? JSON.parse(stored) : true;
    }
    return true;
  });

  const { user } = useContext(appContext);
  const [messageApi, contextHolder] = message.useMessage();

  // Persist sidebar state
  useEffect(() => {
    if (typeof window !== "undefined") {
      localStorage.setItem("mcpSidebar", JSON.stringify(isSidebarOpen));
    }
  }, [isSidebarOpen]);

  const handleSelectWorkbench = (
    workbench: Component<McpWorkbenchConfig> | null
  ) => {
    setCurrentWorkbench(workbench);
  };

  const handleTestConnection = async (
    workbench: Component<McpWorkbenchConfig>
  ) => {
    try {
      setIsLoading(true);
      const isConnected = await mcpAPI.testMcpConnection(workbench);

      if (isConnected) {
        messageApi.success("Connection test successful");
      } else {
        messageApi.error("Connection test failed");
      }
    } catch (error) {
      console.error("Connection test failed:", error);
      messageApi.error("Connection test failed");
    } finally {
      setIsLoading(false);
    }
  };

  if (!user?.id) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-120px)] text-secondary">
        Please log in to use the MCP Playground
      </div>
    );
  }

  return (
    <div className="relative flex h-full w-full">
      {contextHolder}

      {/* Sidebar */}
      <div
        className={`absolute left-0 top-0 h-full transition-all duration-200 ease-in-out ${
          isSidebarOpen ? "w-64" : "w-12"
        }`}
      >
        <McpSidebar
          isOpen={isSidebarOpen}
          onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
          onSelectWorkbench={handleSelectWorkbench}
          isLoading={isLoading}
          currentWorkbench={currentWorkbench}
        />
      </div>

      {/* Main Content */}
      <div
        className={`flex-1 transition-all -mr-6 duration-200 ${
          isSidebarOpen ? "ml-64" : "ml-12"
        }`}
      >
        <div className="p-4 pt-2">
          {/* Breadcrumb */}
          <div className="flex items-center gap-2 mb-4 text-sm">
            <span className="text-primary font-medium">MCP Playground</span>
            {currentWorkbench && (
              <>
                <ChevronRight className="w-4 h-4 text-secondary" />
                <span className="text-secondary">{currentWorkbench.label}</span>
              </>
            )}
          </div>

          {/* Content Area */}
          {isLoading && !currentWorkbench ? (
            <div className="flex items-center justify-center h-[calc(100vh-120px)] text-secondary">
              Loading...
            </div>
          ) : currentWorkbench ? (
            <McpDetail
              workbench={currentWorkbench}
              onTestConnection={() => handleTestConnection(currentWorkbench)}
            />
          ) : (
            <div className="flex items-center justify-center h-[calc(100vh-120px)] text-secondary">
              <div className="text-center">
                <h3 className="text-lg font-medium mb-2">
                  Welcome to MCP Playground
                </h3>
                <p className="text-secondary mb-4">
                  Select an MCP workbench from the sidebar to start testing
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default McpManager;
