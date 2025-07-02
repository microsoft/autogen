import React, { useCallback, useEffect, useState, useContext } from "react";
import { message } from "antd";
import { ChevronRight } from "lucide-react";
import { appContext } from "../../../hooks/provider";
import McpSidebar from "./sidebar";
import McpDetail from "./detail";
import { mcpAPI } from "./api";
import { galleryAPI } from "../gallery/api";
import type {
  Gallery,
  Component,
  McpWorkbenchConfig,
} from "../../types/datamodel";
import { ExclamationTriangleIcon } from "@heroicons/react/24/outline";

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

  // Handle initial URL params
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const galleryId = params.get("galleryId");
    const workbenchIndex = params.get("workbenchIndex");

    if (galleryId && workbenchIndex && !currentWorkbench) {
      // Pass URL params to sidebar to handle initial selection
      // The sidebar will handle the actual workbench loading based on these params
    }
  }, [currentWorkbench]);

  // Handle browser back/forward
  useEffect(() => {
    const handleLocationChange = () => {
      const params = new URLSearchParams(window.location.search);
      const galleryId = params.get("galleryId");
      const workbenchIndex = params.get("workbenchIndex");

      if (!galleryId || !workbenchIndex) {
        // No URL params, clear current workbench
        if (currentWorkbench) {
          setCurrentWorkbench(null);
        }
      }
    };

    window.addEventListener("popstate", handleLocationChange);
    return () => window.removeEventListener("popstate", handleLocationChange);
  }, [currentWorkbench]);

  const handleSelectWorkbench = (
    workbench: Component<McpWorkbenchConfig> | null,
    galleryId?: number,
    workbenchIndex?: number
  ) => {
    setCurrentWorkbench(workbench);

    // Update URL when a workbench is selected
    if (workbench && galleryId !== undefined && workbenchIndex !== undefined) {
      const params = new URLSearchParams(window.location.search);
      params.set("galleryId", galleryId.toString());
      params.set("workbenchIndex", workbenchIndex.toString());
      window.history.pushState({}, "", `?${params.toString()}`);
    } else if (!workbench) {
      // Clear URL params when no workbench is selected
      window.history.pushState({}, "", window.location.pathname);
    }
  };

  const handleGalleryUpdate = async (updatedGallery: Gallery) => {
    if (!user?.id || !updatedGallery.id) return;

    try {
      setIsLoading(true);
      // Sanitize the gallery data by removing timestamps that shouldn't be updated
      const sanitizedUpdates = {
        ...updatedGallery,
        created_at: undefined,
        updated_at: undefined,
      };
      await galleryAPI.updateGallery(
        updatedGallery.id,
        sanitizedUpdates,
        user.id
      );
      messageApi.success("Gallery updated successfully");
    } catch (error) {
      console.error("Failed to update gallery:", error);
      messageApi.error("Failed to update gallery");
    } finally {
      setIsLoading(false);
    }
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
          onGalleryUpdate={handleGalleryUpdate}
        />
      </div>

      {/* Main Content */}
      <div
        className={`flex-1 transition-all -mr-6 duration-200 ${
          isSidebarOpen ? "ml-64" : "ml-12"
        }`}
      >
        <div className="p-4 pt-2">
          <div className="text-xs text-secondary mb-4 border border-dashed rounded-md p-2 ">
            <ExclamationTriangleIcon className="w-4 h-4 inline-block mr-1 text-warning text-orange-500" />{" "}
            MCP Playground is an experimental view for testing MCP Servers in
            your Gallery{" "}
          </div>
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
