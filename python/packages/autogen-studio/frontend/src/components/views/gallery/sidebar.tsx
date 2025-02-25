import React from "react";
import { Button, Tooltip } from "antd";
import {
  Plus,
  Trash2,
  PanelLeftClose,
  PanelLeftOpen,
  Package,
  RefreshCw,
  Globe,
  Info,
} from "lucide-react";
import type { Gallery } from "../../types/datamodel";
import { getRelativeTimeString } from "../atoms";

interface GallerySidebarProps {
  isOpen: boolean;
  galleries: Gallery[];
  currentGallery: Gallery | null;
  onToggle: () => void;
  onSelectGallery: (gallery: Gallery) => void;
  onCreateGallery: () => void;
  onDeleteGallery: (galleryId: number) => void;
  onSyncGallery: (galleryId: number) => void;
  isLoading?: boolean;
}

export const GallerySidebar: React.FC<GallerySidebarProps> = ({
  isOpen,
  galleries,
  currentGallery,
  onToggle,
  onSelectGallery,
  onCreateGallery,
  onDeleteGallery,
  onSyncGallery,
  isLoading = false,
}) => {
  // Render collapsed state
  if (!isOpen) {
    return (
      <div className="h-full border-r border-secondary">
        <div className="p-2 -ml-2">
          <Tooltip title={`Galleries (${galleries.length})`}>
            <button
              onClick={onToggle}
              className="p-2 rounded-md hover:bg-secondary hover:text-accent text-secondary transition-colors focus:outline-none focus:ring-2 focus:ring-accent focus:ring-opacity-50"
            >
              <PanelLeftOpen strokeWidth={1.5} className="h-6 w-6" />
            </button>
          </Tooltip>
        </div>

        <div className="mt-4 px-2 -ml-1">
          <Tooltip title="Create new gallery">
            <Button
              type="text"
              className="w-full p-2 flex justify-center"
              onClick={onCreateGallery}
              icon={<Plus className="w-4 h-4" />}
            />
          </Tooltip>
        </div>
      </div>
    );
  }

  // Render expanded state
  return (
    <div className="h-full border-r border-secondary">
      {/* Header */}
      <div className="flex items-center justify-between pt-0 p-4 pl-2 pr-2 border-b border-secondary">
        <div className="flex items-center gap-2">
          <span className="text-primary font-medium">Galleries</span>
          <span className="px-2 py-0.5 text-xs bg-accent/10 text-accent rounded">
            {galleries.length}
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

      {/* Create Gallery Button */}
      <div className="my-4 flex text-sm">
        <div className="mr-2 w-full">
          <Tooltip title="Create new gallery">
            <Button
              type="primary"
              className="w-full"
              icon={<Plus className="w-4 h-4" />}
              onClick={onCreateGallery}
            >
              New Gallery
            </Button>
          </Tooltip>
        </div>
      </div>

      {/* Section Label */}
      <div className="py-2 flex text-sm text-secondary">
        <div className="flex">All Galleries</div>
        {isLoading && <RefreshCw className="w-4 h-4 ml-2 animate-spin" />}
      </div>

      {/* Galleries List */}
      {!isLoading && galleries.length === 0 && (
        <div className="p-2 mr-2 text-center text-secondary text-sm border border-dashed rounded">
          <Info className="w-4 h-4 inline-block mr-1.5 -mt-0.5" />
          No galleries found
        </div>
      )}

      <div className="scroll overflow-y-auto h-[calc(100%-170px)]">
        {galleries.map((gallery) => (
          <div key={gallery.id} className="relative border-secondary">
            <div
              className={`absolute top-1 left-0.5 z-50 h-[calc(100%-8px)] w-1 bg-opacity-80 rounded ${
                currentGallery?.id === gallery.id ? "bg-accent" : "bg-tertiary"
              }`}
            />
            {gallery && gallery.config && gallery.config.components && (
              <div
                className={`group ml-1 flex flex-col p-3 rounded-l cursor-pointer hover:bg-secondary ${
                  currentGallery?.id === gallery.id
                    ? "border-accent bg-secondary"
                    : "border-transparent"
                }`}
                onClick={() => onSelectGallery(gallery)}
              >
                {/* Gallery Name and Actions Row */}
                <div className="flex items-center justify-between min-w-0">
                  <div className="flex items-center gap-2 min-w-0 flex-1">
                    <div className="truncate flex-1">
                      <span className="font-medium">{gallery.config.name}</span>
                    </div>
                    {gallery.config.url && (
                      <Tooltip title="Remote Gallery">
                        <Globe className="w-3 h-3 text-secondary flex-shrink-0" />
                      </Tooltip>
                    )}
                  </div>
                  <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity ml-2 flex-shrink-0">
                    {gallery.config.url && (
                      <Tooltip title="Sync gallery">
                        <Button
                          type="text"
                          size="small"
                          className="p-0 min-w-[24px] h-6"
                          icon={<RefreshCw className="w-4 h-4" />}
                          onClick={(e) => {
                            e.stopPropagation();
                            onSyncGallery(gallery.id!);
                          }}
                        />
                      </Tooltip>
                    )}
                    <Tooltip
                      title={
                        galleries.length === 1
                          ? "Cannot delete the last gallery"
                          : "Delete gallery"
                      }
                    >
                      <Button
                        type="text"
                        size="small"
                        className="p-0 min-w-[24px] h-6"
                        danger
                        disabled={galleries.length === 1}
                        icon={<Trash2 className="w-4 h-4 text-red-500" />}
                        onClick={(e) => {
                          e.stopPropagation();
                          onDeleteGallery(gallery.id!);
                        }}
                      />
                    </Tooltip>
                  </div>
                </div>

                {/* Gallery Metadata */}
                <div className="mt-1 flex items-center gap-2 text-xs text-secondary">
                  <span className="bg-secondary/20 truncate rounded px-1">
                    v{gallery.config.metadata.version}
                  </span>
                  <div className="flex items-center gap-1">
                    <Package className="w-3 h-3" />
                    <span>
                      {Object.values(gallery.config.components).reduce(
                        (sum, arr) => sum + arr.length,
                        0
                      )}{" "}
                      components
                    </span>
                  </div>
                </div>

                {/* Updated Timestamp */}
                {gallery.updated_at && (
                  <div className="mt-1 flex items-center gap-1 text-xs text-secondary">
                    <span>{getRelativeTimeString(gallery.updated_at)}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default GallerySidebar;
