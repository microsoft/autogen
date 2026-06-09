import React, { useState, useEffect, useContext, useCallback } from "react";
import { Button, Tooltip, Select } from "antd";
import {
  PanelLeftClose,
  PanelLeftOpen,
  Package,
  RefreshCw,
  Info,
  Globe,
} from "lucide-react";
import { appContext } from "../../../hooks/provider";
import { mcpAPI } from "./api";
import type {
  Gallery,
  Component,
  McpWorkbenchConfig,
} from "../../types/datamodel";
import { getRelativeTimeString } from "../atoms";
import Icon from "../../icons";
import { ExclamationTriangleIcon } from "@heroicons/react/24/outline";

const { Option } = Select;

interface McpSidebarProps {
  isOpen: boolean;
  onToggle: () => void;
  onSelectWorkbench: (
    workbench: Component<McpWorkbenchConfig> | null,
    galleryId?: number,
    workbenchIndex?: number
  ) => void;
  isLoading?: boolean;
  currentWorkbench: Component<McpWorkbenchConfig> | null;
  onGalleryUpdate?: (gallery: Gallery) => void;
}

export const McpSidebar: React.FC<McpSidebarProps> = ({
  isOpen,
  onToggle,
  onSelectWorkbench,
  isLoading = false,
  currentWorkbench,
  onGalleryUpdate,
}) => {
  const [galleries, setGalleries] = useState<Gallery[]>([]);
  const [selectedGallery, setSelectedGallery] = useState<Gallery | null>(null);
  const [mcpWorkbenches, setMcpWorkbenches] = useState<
    Component<McpWorkbenchConfig>[]
  >([]);
  const [selectedWorkbenchIndex, setSelectedWorkbenchIndex] =
    useState<number>(-1);
  const [loadingGalleries, setLoadingGalleries] = useState(false);

  const { user } = useContext(appContext);

  // Helper function to get a unique React key for rendering
  const getWorkbenchKey = (
    workbench: Component<McpWorkbenchConfig>,
    index: number
  ) => {
    // Use a hash of the workbench config plus index to ensure uniqueness
    const configStr = JSON.stringify(workbench.config);
    return `${workbench.provider}-${
      workbench.label || "unnamed"
    }-${configStr.slice(0, 20)}-${index}`;
  };

  // Handle gallery selection
  const handleGallerySelect = useCallback((gallery: Gallery) => {
    setSelectedGallery(gallery);
    if (gallery.id) {
      localStorage.setItem("mcp-view-gallery", gallery.id.toString());
    }

    // Extract MCP workbenches from the selected gallery
    const workbenches = mcpAPI.extractMcpWorkbenches(gallery);
    setMcpWorkbenches(workbenches);
    // Reset selection - let the effect handle workbench selection
    setSelectedWorkbenchIndex(-1);
  }, []);

  // Load galleries on component mount
  const loadGalleries = useCallback(async () => {
    if (!user?.id) return;

    try {
      setLoadingGalleries(true);
      const galleriesData = await mcpAPI.listGalleries(user.id);
      setGalleries(galleriesData);

      // Select gallery based on URL params first, then localStorage, then first gallery
      const params = new URLSearchParams(window.location.search);
      const urlGalleryId = params.get("galleryId");
      const savedGalleryId = localStorage.getItem("mcp-view-gallery");
      let galleryToSelect = galleriesData[0];

      if (urlGalleryId) {
        // Prioritize URL parameter
        const urlGallery = galleriesData.find(
          (g) => g.id?.toString() === urlGalleryId
        );
        if (urlGallery) {
          galleryToSelect = urlGallery;
        }
      } else if (savedGalleryId) {
        // Fall back to localStorage
        const savedGallery = galleriesData.find(
          (g) => g.id?.toString() === savedGalleryId
        );
        if (savedGallery) {
          galleryToSelect = savedGallery;
        }
      }

      if (galleryToSelect) {
        // Set gallery and workbenches, but don't trigger selection here
        setSelectedGallery(galleryToSelect);
        if (galleryToSelect.id) {
          localStorage.setItem(
            "mcp-view-gallery",
            galleryToSelect.id.toString()
          );
        }

        const workbenches = mcpAPI.extractMcpWorkbenches(galleryToSelect);
        setMcpWorkbenches(workbenches);

        // Let the effect below handle the workbench selection
      }
    } catch (error) {
      console.error("Failed to load galleries:", error);
    } finally {
      setLoadingGalleries(false);
    }
  }, [user?.id]);

  useEffect(() => {
    loadGalleries();
  }, [loadGalleries]);

  // Handle workbench selection after galleries/workbenches are loaded
  useEffect(() => {
    if (mcpWorkbenches.length > 0 && selectedGallery && !loadingGalleries) {
      // Check for URL parameters to restore workbench selection
      const params = new URLSearchParams(window.location.search);
      const urlGalleryId = params.get("galleryId");
      const urlWorkbenchIndex = params.get("workbenchIndex");

      let indexToSelect = 0; // Default to first workbench

      // If URL params match current gallery, try to select the specified workbench
      if (
        urlGalleryId &&
        urlWorkbenchIndex &&
        selectedGallery.id?.toString() === urlGalleryId
      ) {
        const urlIndex = parseInt(urlWorkbenchIndex);
        if (urlIndex >= 0 && urlIndex < mcpWorkbenches.length) {
          indexToSelect = urlIndex;
        }
      }

      // Only update if selection has changed
      if (selectedWorkbenchIndex !== indexToSelect) {
        setSelectedWorkbenchIndex(indexToSelect);
        onSelectWorkbench(
          mcpWorkbenches[indexToSelect],
          selectedGallery.id,
          indexToSelect
        );
      }
    } else if (
      mcpWorkbenches.length === 0 &&
      selectedWorkbenchIndex !== -1 &&
      !loadingGalleries
    ) {
      // No workbenches available, clear selection
      setSelectedWorkbenchIndex(-1);
      onSelectWorkbench(null);
    }
  }, [mcpWorkbenches, selectedGallery, onSelectWorkbench, loadingGalleries]); // Add loadingGalleries to prevent premature execution

  // Render collapsed state
  if (!isOpen) {
    return (
      <div className="h-full border-r border-secondary">
        <div className="p-2 -ml-2">
          <Tooltip title={`MCP Workbenches (${mcpWorkbenches.length})`}>
            <button
              onClick={onToggle}
              className="p-2 rounded-md hover:bg-secondary hover:text-accent text-secondary transition-colors focus:outline-none focus:ring-2 focus:ring-accent focus:ring-opacity-50"
            >
              <PanelLeftOpen strokeWidth={1.5} className="h-6 w-6" />
            </button>
          </Tooltip>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full border-r border-secondary bg-primary">
      {/* Header */}
      <div className="flex items-center justify-between pt-0 p-4 pl-2 pr-2 border-b border-secondary">
        <div className="flex sticky items-center gap-2">
          <span className="text-primary font-medium">MCP Playground</span>
          <span className="px-2 py-0.5 text-xs bg-accent/10 text-accent rounded">
            {mcpWorkbenches.length}
          </span>
        </div>
        <Tooltip title="Close Sidebar">
          <button
            onClick={onToggle}
            className="p-2 rounded-md hover:bg-secondary hover:text-accent text-secondary transition-colors focus:outline-none focus:ring-2 focus:ring-accent focus:ring-opacity-50"
          >
            <PanelLeftClose strokeWidth={1.5} className="h-6 w-6" />
          </button>
        </Tooltip>
      </div>

      {/* Gallery Selection */}
      <div className="p-4 pl-2 border-b border-secondary">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-secondary">Gallery</span>
          <Tooltip title="Refresh galleries">
            <Button
              size="small"
              icon={
                loadingGalleries ? (
                  <RefreshCw className="w-3 h-3 animate-spin" />
                ) : (
                  <RefreshCw className="w-3 h-3" />
                )
              }
              className="border-0 hover:bg-secondary"
              onClick={loadGalleries}
              disabled={loadingGalleries}
            />
          </Tooltip>
        </div>
        <Select
          className="w-full"
          placeholder="Select a gallery"
          value={selectedGallery?.id}
          onChange={(galleryId) => {
            const gallery = galleries.find((g) => g.id === galleryId);
            if (gallery) handleGallerySelect(gallery);
          }}
          loading={loadingGalleries}
        >
          {galleries.map((gallery) => (
            <Option key={gallery.id} value={gallery.id}>
              <div className="flex items-center gap-2">
                <Package className="w-3 h-3" />
                <span>{gallery.config.name}</span>
                {gallery.config.url && (
                  <Globe className="w-3 h-3 text-secondary" />
                )}
              </div>
            </Option>
          ))}
        </Select>
      </div>

      {/* Section Label */}
      <div className="py-2 flex text-sm text-secondary px-4">
        <div className="flex">
          MCP Workbenches
          {isLoading && <RefreshCw className="w-4 h-4 ml-2 animate-spin" />}
        </div>
      </div>

      {/* Workbenches List */}
      {!selectedGallery && (
        <div className="p-2 mr-2 text-center text-secondary text-sm border border-dashed rounded mx-4">
          <Info className="w-4 h-4 inline-block mr-1.5 -mt-0.5" />
          Select a gallery to view MCP workbenches
        </div>
      )}

      {selectedGallery && mcpWorkbenches.length === 0 && (
        <div className="p-2 mr-2 text-center text-secondary text-sm border border-dashed rounded ml-2">
          <Info className="w-4 h-4 inline-block mr-1.5 -mt-0.5" />
          No MCP workbenches found in this gallery
        </div>
      )}

      <div className="scroll overflow-y-auto h-[calc(100%-230px)]">
        {mcpWorkbenches.map((workbench, index) => {
          const workbenchKey = getWorkbenchKey(workbench, index);
          const isSelected = index === selectedWorkbenchIndex;

          return (
            <div key={workbenchKey} className="relative border-secondary">
              <div
                className={`absolute top-1 left-0.5 z-50 h-[calc(100%-8px)] w-1 bg-opacity-80 rounded ${
                  isSelected ? "bg-accent" : "bg-tertiary"
                }`}
              />
              <div
                className={`group ml-1 flex flex-col p-3 rounded-l cursor-pointer hover:bg-secondary ${
                  isSelected
                    ? "border-accent bg-secondary"
                    : "border-transparent"
                }`}
                onClick={() => {
                  setSelectedWorkbenchIndex(index);
                  onSelectWorkbench(workbench, selectedGallery?.id, index);
                }}
              >
                {/* Workbench Name and Actions Row */}
                <div className="flex items-center justify-between min-w-0">
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <Icon
                      icon="mcp"
                      size={4}
                      className="w-4 h-4 text-accent flex-shrink-0"
                    />
                    <div className="truncate flex-1 text-sm">
                      <span className="font-medium">{workbench.label}</span>
                    </div>
                  </div>
                </div>

                {/* Workbench Details */}
                <div className="mt-1 text-sm text-secondary">
                  <div className="flex items-center gap-2">
                    <span className="truncate text-xs">
                      {workbench.config.server_params?.type?.replace(
                        "ServerParams",
                        ""
                      ) || "Unknown Type"}
                    </span>
                  </div>
                  {/* {workbench.description && (
                    <div className="mt-1 text-xs text-secondary truncate">
                      {workbench.description}
                    </div>
                  )} */}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Footer */}
      {selectedGallery && (
        <div className="p-3 border-t border-secondary text-sm text-secondary">
          <div className="flex items-center justify-between">
            <span className="truncate flex-1">
              {selectedGallery.config.name}
            </span>
            <span className="ml-2 flex-shrink-0">
              {mcpWorkbenches.length} MCP workbench
              {mcpWorkbenches.length !== 1 ? "es" : ""}
            </span>
          </div>
          {selectedGallery.updated_at && (
            <div className="text-xs text-tertiary mt-1">
              Updated {getRelativeTimeString(selectedGallery.updated_at)}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default McpSidebar;
