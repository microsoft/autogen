import React, { useState, useRef } from "react";
import { Button, message, Tooltip } from "antd";
import {
  Package,
  Users,
  Bot,
  Globe,
  RefreshCw,
  Edit2,
  X,
  Wrench,
  Brain,
  Timer,
  Save,
  ChevronUp,
  ChevronDown,
  Edit,
} from "lucide-react";
import type { Gallery } from "./types";
import { useGalleryStore } from "./store";
import { MonacoEditor } from "../monaco";
import { ComponentConfigTypes } from "../../types/datamodel";
import { getRelativeTimeString, TruncatableText } from "../atoms";

const ComponentGrid: React.FC<{
  title: string;
  icon: React.ReactNode;
  items: ComponentConfigTypes[];
}> = ({ title, icon, items }) => {
  const [isExpanded, setIsExpanded] = useState(true);

  return (
    <div className="bg-tertiary rounded    p-2">
      <div
        className="flex items-center justify-between cursor-pointer mb-2"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2">
          <span className="text-primary">{icon}</span>
          <span className="text-sm capitalize">
            {items.length} {items.length === 1 ? title : `${title}s`}
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-primary" />
        ) : (
          <ChevronDown className="w-4 h-4 text-primary" />
        )}
      </div>

      <div
        className={`space-y-2 transition-all duration-200 ${
          isExpanded ? "max-h-[500px]" : "max-h-0"
        } overflow-hidden`}
      >
        {items.map((item, idx) => (
          <div
            key={idx}
            className="bg-secondary rounded p-3 hover:bg-tertiary transition-colors"
          >
            <div className="text-sm font-medium truncate">
              {item.component_type}
            </div>
            {item.description && (
              <p className="text-xs text-primary mt-1 ">
                <TruncatableText
                  content={item.description}
                  textThreshold={150}
                />
              </p>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

interface GalleryDetailProps {
  gallery: Gallery;
  onSave: (updates: Partial<Gallery>) => void;
  onDirtyStateChange: (isDirty: boolean) => void;
}

export const GalleryDetail: React.FC<GalleryDetailProps> = ({
  gallery,
  onSave,
  onDirtyStateChange,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [jsonValue, setJsonValue] = useState(JSON.stringify(gallery, null, 2));
  const editorRef = useRef(null);
  const { syncGallery, getLastSyncTime } = useGalleryStore();

  const handleSync = async () => {
    if (!gallery.url) return;

    setIsSyncing(true);
    try {
      await syncGallery(gallery.id);
      message.success("Gallery synced successfully");
    } catch (error) {
      message.error("Failed to sync gallery");
    } finally {
      setIsSyncing(false);
    }
  };

  const handleJsonChange = (value: string) => {
    setJsonValue(value);
    onDirtyStateChange(true);
  };

  const handleSave = async () => {
    try {
      const parsedGallery = JSON.parse(jsonValue);
      const updatedGallery = {
        ...parsedGallery,
        id: gallery.id,
        metadata: {
          ...parsedGallery.metadata,
          updated_at: new Date().toISOString(),
        },
      };
      await onSave(updatedGallery);
      onDirtyStateChange(false);
      setIsEditing(false);
      message.success("Gallery updated successfully");
    } catch (error) {
      message.error("Invalid JSON format");
    }
  };

  const gridItems = [
    {
      icon: <Users className="w-4 h-4" />,
      title: "team",
      items: gallery.items.teams,
    },
    {
      icon: <Bot className="w-4 h-4" />,
      title: "agent",
      items: gallery.items.components.agents,
    },
    {
      icon: <Wrench className="w-4 h-4" />,
      title: "tool",
      items: gallery.items.components.tools,
    },
    {
      icon: <Brain className="w-4 h-4" />,
      title: "model",
      items: gallery.items.components.models,
    },
    {
      icon: <Timer className="w-4 h-4" />,
      title: "termination",
      items: gallery.items.components.terminations,
    },
  ];

  return (
    <div className="space-y-6">
      {/* Banner Section - Kept unchanged */}
      <div className="relative h-72 rounded bg-secondary overflow-hidden">
        <img
          src="/images/bg/layeredbg.svg"
          alt="Gallery Banner"
          className="absolute w-full h-full object-cover"
        />
        <div className="relative z-10 p-6 h-full flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-medium text-primary">
                {gallery.name}
              </h1>
              {gallery.url && (
                <Tooltip title="Remote Gallery">
                  <Globe className="w-5 h-5 text-secondary" />
                </Tooltip>
              )}
            </div>
            <p className="text-secondary w-1/2 mt-2 line-clamp-3">
              {gallery.metadata.description}
            </p>
            <p className="text-secondary text-sm mt-2">
              {gallery.metadata.author}
            </p>
          </div>

          <div className="flex gap-2">
            <div className="bg-tertiary backdrop-blur rounded p-2 flex items-center gap-2">
              <Package className="w-4 h-4 text-secondary" />
              <span className="text-sm">
                {Object.values(gallery.items.components).reduce(
                  (sum, arr) => sum + arr.length,
                  0
                )}{" "}
                components
              </span>
            </div>
            <div className="bg-tertiary backdrop-blur rounded p-2 text-sm">
              v{gallery.metadata.version}
            </div>
            {gallery.metadata.tags?.map((tag) => (
              <div
                key={tag}
                className="bg-tertiary backdrop-blur rounded p-2 px-2 text-sm"
              >
                {tag}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex justify-end gap-2">
        {gallery.url && (
          <Tooltip
            title={
              getLastSyncTime(gallery.id)
                ? `Last synced: ${getRelativeTimeString(
                    getLastSyncTime(gallery.id) || ""
                  )}`
                : "Never synced"
            }
          >
            <Button
              icon={
                <RefreshCw
                  className={(isSyncing ? "animate-spin" : "") + " w-4 h-4"}
                />
              }
              loading={isSyncing}
              onClick={handleSync}
            >
              Sync
            </Button>
          </Tooltip>
        )}
        {!isEditing ? (
          <Button
            icon={<Edit className="w-4 h-4" />}
            onClick={() => setIsEditing(true)}
          >
            Edit
          </Button>
        ) : (
          <>
            <Button
              icon={<X className="w-4 h-4" />}
              onClick={() => setIsEditing(false)}
            >
              Cancel
            </Button>
            <Button type="primary" onClick={handleSave}>
              Save Changes
            </Button>
          </>
        )}
      </div>

      {/* Grid Layout */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {gridItems.map((item) => (
          <ComponentGrid
            key={item.title}
            title={item.title}
            icon={item.icon}
            items={item.items}
          />
        ))}
      </div>

      {/* Editor Section */}
      {isEditing && (
        <div
          className="fixed bottom-0 left-0 right-0 bg-primary z-50 shadow-lg transition-transform duration-300 ease-in-out transform"
          style={{ height: "70vh" }}
        >
          <div className="border-b border-secondary p-4 flex justify-between items-center">
            <h3 className="text-normal font-medium">
              Edit Gallery Configuration
            </h3>
            <div className="inline-flex gap-2">
              <Tooltip title="Save Changes">
                <Button
                  icon={<Save className="w-4 h-4" />}
                  onClick={handleSave}
                />
              </Tooltip>
              <Tooltip title="Cancel Editing">
                <Button
                  icon={<X className="w-4 h-4" />}
                  onClick={() => setIsEditing(false)}
                />
              </Tooltip>
            </div>
          </div>
          <div className="h-[calc(100%-60px)]">
            <MonacoEditor
              value={jsonValue}
              onChange={handleJsonChange}
              editorRef={editorRef}
              language="json"
              minimap={true}
            />
          </div>
        </div>
      )}
    </div>
  );
};
